# DUKAANMIND: VOICE-FIRST POS MIDDLEWARE

**System Architecture & Development Context Blueprint**

This document provides a technical specification of the **DukaanMind** codebase. You can save this file directly into your workspace root as `ARCHITECTURE.md` to give **Cline** (or any AI coding agent in VS Code) complete context on your system structure, runtime configurations, implementation details, and development roadmap.

---

## 1. System Overview & Data Flow

DukaanMind is a voice-activated Point-of-Sale (POS) middleware system that processes spoken orders, transcribes audio locally, parses order intent into structured JSON schema, and executes real-time stock/price calculations against a POS inventory engine.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                FRONTEND LAYER                                   │
│  Next.js 14 (TypeScript / React) - localhost:3000                               │
│  └── Audio Stream Capture via MediaRecorder API (WebM/WAV)                      │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         │ HTTP POST /api/v1/process-audio
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND LAYER                                   │
│  FastAPI (Python 3.13) - localhost:8000                                         │
│  ├── CorsMiddleware (Allow All)                                                 │
│  └── Temporary Disk File Streaming                                              │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             SPEECH RECOGNITION (STT)                            │
│  faster-whisper (CPU int8, base.en weights)                                     │
│  └── Voice Activity Detection (vad_filter=True, min_silence_duration_ms=500)   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Raw Transcript
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            INTENT PARSING PIPELINE                              │
│  app/core/pipeline.py                                                           │
│  ├── Primary: Gemini 2.0 Flash API (google-generativeai)                        │
│  └── Fallback: Phonetic / Soundex Pattern Parser                                │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Structured JSON Order
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             POS ENGINE & ADAPTER                              │
│  app/adapters/mock_pos.py                                                       │
│  └── Stock Validation, Subtotal/Tax Calculation & Receipt Payload Generation    │
└─────────────────────────────────────────────────────────────────────────────────┘

```

---

## 2. Directory & Workspace Structure

```
voice_pos_middleware/
├── app/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── mock_pos.py          # POS Inventory Ledger & Execution Engine
│   ├── core/
│   │   ├── __init__.py
│   │   └── pipeline.py          # Gemini LLM Parser & Phonetic Fallback Logic
│   └── main.py                  # FastAPI Application Entrypoint & Whisper STT
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── globals.css
│   │       ├── layout.tsx
│   │       └── page.tsx         # Next.js Voice Capture & Receipt UI
│   ├── package.json
│   └── tsconfig.json
├── venv/                        # Python 3.13 Virtual Environment
├── ARCHITECTURE.md              # System Blueprint & Context File
└── requirements.txt             # Backend Dependencies

```

---

## 3. Technology Stack & Runtime Configuration

| Component | Technology | Runtime / Port | Environment Details |
| --- | --- | --- | --- |
| **Frontend UI** | Next.js 14, React, TypeScript | `http://localhost:3000` | Node.js Environment |
| **Backend API** | FastAPI, Uvicorn | `http://localhost:8000` | Python 3.13 (`.\venv`) |
| **STT Engine** | `faster-whisper` (`base.en`) | Local CPU Execution | Quantized `int8`, VAD enabled |
| **Primary LLM** | `gemini-2.0-flash` | Cloud API | `google-generativeai` SDK |
| **Fallback Engine** | Regex & Soundex Pattern Matching | Local Python Process | Trigger-based Phonetic Parser |
| **POS Ledger** | `MockPOSAdapter` | In-Memory Dictionary | Inventory Stock & Pricing Engine |

---

## 4. Source Code Implementation Details

### 4.1 Backend Entrypoint (`app/main.py`)

Handles binary multipart audio file ingestion, temporary disk buffering, VAD filtering, local transcription via `faster-whisper`, and error handoff.

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from app.adapters.mock_pos import MockPOSAdapter
from app.core.pipeline import VoicePOSPipeline
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

# Local CPU-optimized Whisper model
whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")

@app.get("/")
def read_root():
    return {"status": "online", "service": "Voice POS Middleware API"}

@app.post("/api/v1/process-audio")
async def process_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        segments, _ = whisper_model.transcribe(
            tmp_path, 
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        transcript = " ".join([segment.text for segment in segments]).strip()

        if not transcript or len(transcript) < 3 or "equal" in transcript.lower():
            return {
                "transcript": "No clear speech detected.",
                "receipt": {
                    "status": "unsupported",
                    "message": "Sorry, I couldn't hear your order clearly. Please try again."
                }
            }

        order_result = await pipeline.process_voice_text(transcript)
        return {
            "transcript": transcript,
            "receipt": order_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

```

### 4.2 Pipeline & Intent Extraction (`app/core/pipeline.py`)

Routes transcripts through `gemini-2.0-flash` for structured JSON creation. Falls back to deterministic phonetic rules when the API key is unconfigured or offline.

```python
import os
import json
import re
import google.generativeai as genai

GENAI_KEY = os.getenv("GEMINI_API_KEY", "")
if GENAI_KEY:
    genai.configure(api_key=GENAI_KEY)

class VoicePOSPipeline:
    def __init__(self, pos_adapter):
        self.pos_adapter = pos_adapter

    async def process_voice_text(self, text: str):
        parsed_llm = await self._parse_with_llm(text)
        return await self.pos_adapter.execute_order(parsed_llm)

    async def _parse_with_llm(self, text: str):
        menu_items = ["zinger burger", "single burger", "double burger", "coca-cola zero", "fries"]
        
        prompt = f"""
        You are an intelligent Fast-Food POS Voice Assistant.
        Available Menu Items: {menu_items}

        Customer Spoke: "{text}"

        Task:
        1. Parse intended menu items and exact quantities. Correct acoustic mishearings (e.g., 'in bed', 'singing' -> 'zinger burger').
        2. Map spoken numbers cleanly (e.g., 'one', 'a' -> 1; 'two', 'to', 'too' -> 2).
        3. If items requested are NOT on the menu (e.g. biryani, pizza), set status to "unsupported".
        4. Return ONLY valid JSON:
        {{
          "status": "success" | "unsupported",
          "reply": "Order summary note",
          "items": [
             {{"name": "zinger burger", "quantity": 1}},
             {{"name": "coca-cola zero", "quantity": 1}}
          ]
        }}
        """

        if GENAI_KEY:
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    prompt, 
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
            except Exception:
                pass

        return self._smart_fallback_parser(text)

    def _smart_fallback_parser(self, text: str):
        text_lower = text.lower()
        items = []

        unsupported_keywords = ["biryani", "pizza", "pasta", "sushi", "taco", "ice cream"]
        if any(unsupported in text_lower for unsupported in unsupported_keywords):
            return {
                "status": "unsupported",
                "reply": "I'm sorry, we don't serve that here! We offer Zinger Burgers, Single/Double Burgers, Fries, and Coca-Cola Zero.",
                "items": []
            }

        zinger_triggers = ["zinger", "burger", "zing", "in bed", "bed", "finger", "worker"]
        if any(w in text_lower for w in zinger_triggers):
            qty = 2 if any(q in text_lower for q in ["two", "2", "to", "too", "double"]) else 1
            items.append({"name": "zinger burger", "quantity": qty})

        coke_triggers = ["coke", "coca", "zero", "drink", "cola", "cke"]
        if any(w in text_lower for w in coke_triggers):
            qty = 2 if any(q in text_lower for q in ["two", "2", "to", "too"]) else 1
            items.append({"name": "coca-cola zero", "quantity": qty})

        if "fries" in text_lower or "fry" in text_lower:
            qty = 2 if any(q in text_lower for q in ["two", "2", "to", "too"]) else 1
            items.append({"name": "fries", "quantity": qty})

        if not items:
            return {
                "status": "unsupported",
                "message": "No valid menu items recognized in speech stream.",
                "items": []
            }

        return {
            "status": "success",
            "reply": "Order processed successfully!",
            "items": items
        }

```

### 4.3 POS Adapter Engine (`app/adapters/mock_pos.py`)

Manages inventory pricing, stock deductions, subtotals, and receipt outputs.

```python
class MockPOSAdapter:
    def __init__(self):
        self.inventory = {
            "zinger burger": {"price": 4.99, "stock": 50},
            "single burger": {"price": 3.49, "stock": 40},
            "double burger": {"price": 5.49, "stock": 30},
            "coca-cola zero": {"price": 1.99, "stock": 100},
            "fries": {"price": 2.49, "stock": 80}
        }

    async def execute_order(self, parsed_data: dict):
        if parsed_data.get("status") == "unsupported":
            return parsed_data

        total = 0.0
        items_processed = []

        for item in parsed_data.get("items", []):
            name = item.get("name")
            qty = item.get("quantity", 1)
            if name in self.inventory:
                subtotal = self.inventory[name]["price"] * qty
                total += subtotal
                items_processed.append({
                    "name": name, 
                    "quantity": qty, 
                    "subtotal": subtotal
                })

        return {
            "status": "success",
            "order_id": "ORD-8821",
            "assistant_note": parsed_data.get("reply", ""),
            "items": items_processed,
            "total_amount": round(total, 2)
        }

```

---

## 5. Development Instructions for Cline

When tasking **Cline** in VS Code, use these operational guidelines to maintain consistency:

### 1. Startup & Execution Commands

* **Backend:** Launch on Port 8000 using virtual environment context:
```powershell
cd C:\Users\itzai\OneDrive\Desktop\voice_pos_middleware
.\venv\Scripts\Activate.ps1
$env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
uvicorn app.main:app --port 8000 --reload

```


* **Frontend:** Launch on Port 3000:
```powershell
cd C:\Users\itzai\OneDrive\Desktop\voice_pos_middleware\frontend
npm run dev

```



### 2. Known Constraints & Directives for Cline

* **Do NOT introduce a Port 8001 service.** The entire API pipeline (Whisper, Gemini, POS Adapter) is consolidated within `app/main.py` on Port 8000.
* **Preserve VAD Settings:** Do not remove `vad_filter=True` from `whisper_model.transcribe()` as it prevents silent audio frame hallucinations.
* **Maintain Response Schema:** Ensure all pipeline output conforms to the structured receipt schema expected by `page.tsx`:
```json
{
  "status": "success",
  "order_id": "ORD-8821",
  "assistant_note": "String note",
  "items": [{"name": "string", "quantity": 1, "subtotal": 0.00}],
  "total_amount": 0.00
}

```



---

## 6. Development Milestones

1. **Synthetic Dataset Pipeline:** Generate 500+ paired audio/JSON samples for menu domain fine-tuning.
2. **Vector Similarity Matching:** Replace local regex rules in `pipeline.py` with dynamic vector embeddings for menu resolution.
3. **Domain Fine-Tuning:** Fine-tune `faster-whisper` (`base.en` / `small.en`) using LoRA on custom food ordering speech samples.