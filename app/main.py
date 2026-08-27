from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from faster_whisper import WhisperModel
from app.adapters.mock_pos import MockPOSAdapter
from app.core.langgraph_pipeline import VoicePOSPipeline  # Updated to LangGraph pipeline
from app.core.tts_engine import get_tts_engine
from app.core.rag_engine import get_rag_engine
from app.schemas.tts import TTSRequest, TTSResponse
from app.schemas.rag import QARequest, QAResponse
import shutil
import tempfile
import os

app = FastAPI(title="Voice POS Middleware", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pos_adapter = MockPOSAdapter()
pipeline = VoicePOSPipeline(pos_adapter)

# Initialize Whisper model with English optimization
whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")

# Initialize RAG engine
rag_engine = get_rag_engine()

# Dynamic menu vocabulary - populated at startup
MENU_VOCAB = "Zinger Burger, Single Burger, Double Burger, Coca-Cola Zero, Fries, Peppy"


@app.on_event("startup")
async def load_menu_vocab():
    """Fetch menu from POS adapter and build Whisper initial_prompt dynamically."""
    global MENU_VOCAB
    try:
        products = await pos_adapter.fetch_products()
        if products:
            # Use exact product names from POS for best Whisper biasing
            MENU_VOCAB = ", ".join(p["name"] for p in products)
            print(f"[Whisper] Dynamic vocabulary loaded: {MENU_VOCAB}")
        else:
            print("[Whisper] No products found, using fallback vocabulary")
    except Exception as e:
        print(f"[Whisper] Failed to load dynamic vocabulary: {e}")


@app.get("/")
def read_root():
    return {"status": "online", "service": "Voice POS Middleware API"}

@app.post("/api/v1/process-audio")
async def process_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Transcribe audio with VAD filter to ignore silence & static
        segments, _ = whisper_model.transcribe(
            tmp_path, 
            beam_size=5,
            vad_filter=True,  # Drops background silence/noise automatically
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=MENU_VOCAB,
        )
        transcript = " ".join([segment.text for segment in segments]).strip()

        # Catch empty or purely hallucinated static transcripts
        if not transcript or len(transcript) < 3 or "equal" in transcript.lower():
            return {
                "transcript": "No clear speech detected. Please speak closer to the mic.",
                "receipt": {
                    "status": "unsupported",
                    "message": "Sorry, I couldn't hear your order clearly. Please tap the mic and try again."
                }
            }

        order_result = await pipeline.process_voice_text(transcript)
        
        # Generate TTS for the receipt summary (async)
        tts = get_tts_engine()
        tts_text = order_result.get("assistant_note", "Order processed successfully!")
        if order_result.get("items"):
            item_summary = ", ".join([f"{item['quantity']} {item['name']}" for item in order_result["items"]])
            tts_text = f"You ordered {item_summary}. Total is ${order_result.get('total_amount', 0):.2f}. {tts_text}"
        
        audio_base64 = await tts.synthesize_base64(tts_text)
        order_result["assistant_audio_base64"] = audio_base64
        
        return {
            "transcript": transcript,
            "receipt": order_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/v1/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using Edge TTS."""
    try:
        tts = get_tts_engine(request.voice)
        audio_base64 = await tts.synthesize_base64(request.text)
        
        return TTSResponse(
            audio_base64=audio_base64,
            duration_ms=len(request.text) * 50,  # Rough estimate
            voice=request.voice
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

@app.post("/api/v1/tts/stream")
async def text_to_speech_stream(request: TTSRequest):
    """Stream TTS audio chunks for low-latency playback."""
    try:
        tts = get_tts_engine(request.voice)
        
        async def audio_generator():
            async for chunk in tts.synthesize_stream(request.text):
                yield chunk
        
        return StreamingResponse(
            audio_generator(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=tts_{request.voice}.mp3",
                "X-Voice": request.voice
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS streaming error: {str(e)}")

@app.post("/api/v1/menu-qa", response_model=QAResponse)
async def menu_qa(request: QARequest):
    """Query the menu knowledge base using RAG."""
    try:
        result = await rag_engine.query(
            question=request.question,
            k=request.k,
            similarity_threshold=request.similarity_threshold
        )
        return QAResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query error: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint with model status."""
    tts = get_tts_engine()
    rag_ready = rag_engine.is_ready()
    return {
        "status": "healthy",
        "whisper": "loaded",
        "tts": "ready",
        "tts_voice": tts.voice_key,
        "available_voices": list(tts.list_voices().keys()),
        "rag": "ready" if rag_ready else "not_initialized"
    }
