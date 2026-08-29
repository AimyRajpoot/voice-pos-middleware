import re
import time
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from dotenv import load_dotenv
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path)

from order_state import OrderState
from adapters import BurgerBarnAdapter, PizzaPlazaAdapter, NormalizedItem
from llm.openrouter_client import OpenRouterClient
from stt.parakeet_engine import ParakeetSTT
from tts.deepgram_flux import DeepgramFluxTTS


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

order_state = OrderState()
order_state.adapter = BurgerBarnAdapter()

parakeet_stt: Optional[ParakeetSTT] = None
llm_client: Optional[OpenRouterClient] = None
tts_client: Optional[DeepgramFluxTTS] = None
conversation_history: list[dict] = []


def get_llm_client():
    global llm_client
    if llm_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
        llm_client = OpenRouterClient(api_key)
    return llm_client


def get_tts_client():
    global tts_client
    if tts_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
        tts_client = DeepgramFluxTTS(api_key)
    return tts_client


@app.on_event("startup")
async def startup_event():
    global parakeet_stt
    try:
        parakeet_stt = ParakeetSTT()
    except Exception as e:
        print(f"Warning: Could not load Parakeet model: {e}")
        parakeet_stt = None


class TranscriptRequest(BaseModel):
    audio: str


class SwitchBusinessRequest(BaseModel):
    business: str


@app.get("/")
async def root():
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return FileResponse(frontend_path)


@app.get("/menu")
async def get_menu():
    if order_state.adapter is None:
        raise HTTPException(status_code=500, detail="No business selected")
    menu = order_state.adapter.get_menu()
    return {
        "business": order_state.current_business,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "price": item.price,
                "in_stock": item.in_stock,
                "modifiers": [{"name": m.name, "extra_price": m.extra_price} for m in item.modifiers]
            }
            for item in menu
        ]
    }


@app.post("/switch-business")
async def switch_business(req: SwitchBusinessRequest):
    global conversation_history
    if req.business == "burger_barn":
        order_state.adapter = BurgerBarnAdapter()
        order_state.current_business = "burger_barn"
    elif req.business == "pizza_plaza":
        order_state.adapter = PizzaPlazaAdapter()
        order_state.current_business = "pizza_plaza"
    else:
        raise HTTPException(status_code=400, detail="Invalid business name")
    conversation_history = []
    order_state.clear_order()
    return {"status": "ok", "business": order_state.current_business}


@app.get("/order")
async def get_order():
    return order_state.to_dict()


@app.post("/order/clear")
async def clear_order():
    order_state.clear_order()
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(req: TranscriptRequest):
    if parakeet_stt is None:
        raise HTTPException(status_code=500, detail="STT not available")
    audio_data = base64.b64decode(req.audio)
    transcript = parakeet_stt.transcribe(audio_data)
    return {"transcript": transcript}


@app.post("/chat")
async def chat(req: TranscriptRequest):
    audio_data = base64.b64decode(req.audio)
    timings = {}
    
    if parakeet_stt is None:
        raise HTTPException(status_code=500, detail="STT not available")
    
    stt_start = time.time()
    transcript = parakeet_stt.transcribe(audio_data)
    timings["stt_seconds"] = round(time.time() - stt_start, 3)
    
    if not transcript:
        return {"transcript": "", "response": "", "audio": None, "order": order_state.to_dict(), "timings": timings}
    
    transcript_lower = transcript.lower().strip()
    
    # Check for order confirmation
    confirm_phrases = ["yes", "yeah", "confirm", "that's all", "done", "that's it", "no more", "place order", "submit order", "complete order", "finish order", "order confirmed"]
    if any(phrase in transcript_lower for phrase in confirm_phrases) and len(order_state.items) > 0:
        order_state.clear_order()
        return {
            "transcript": transcript,
            "response": "Order confirmed! Thank you for ordering. Your order has been placed successfully.",
            "audio": None,
            "order": order_state.to_dict(),
            "timings": timings
        }
    
    # Get menu for context
    menu = order_state.adapter.get_menu()
    menu_str = "\n".join([f"- {item.name}: ${item.price} ({item.category})" for item in menu])
    
    # Get current order for context
    current_order = order_state.to_dict()
    if current_order['items']:
        order_items_str = "\n".join([f"{i+1}. {item['name']} x{item['quantity']} - ${item['price']*item['quantity']:.2f}" for i, item in enumerate(current_order['items'])])
        order_summary = f"Current order:\n{order_items_str}\nTotal: ${current_order['total']:.2f}"
    else:
        order_summary = "No items in order yet."
    
    client = get_llm_client()
    
    llm_start = time.time()
    try:
        response_text = client.simple_chat(transcript, menu_str, order_summary, conversation_history)
    except Exception as e:
        print(f"LLM error: {e}")
        return {"transcript": transcript, "response": "", "audio": None, "order": order_state.to_dict(), "timings": timings, "error": str(e)}
    
    timings["llm_seconds"] = round(time.time() - llm_start, 3)
    
    # Parse response for actions
    actions = client.parse_actions(response_text)
    for action_type, item_name, qty in actions:
        if action_type == 'add':
            # Find item in menu
            for menu_item in menu:
                if item_name.lower() in menu_item.name.lower():
                    order_state.add_item(menu_item.id, menu_item.name, qty, menu_item.price)
                    order_state.adapter.update_stock(menu_item.id, qty)
                    break
        elif action_type == 'remove':
            if 0 <= qty < len(order_state.items):
                removed_item = order_state.items[qty]
                order_state.adapter.restore_stock(removed_item.item_id, removed_item.quantity)
                order_state.remove_item(qty)
    
    conversation_history.append({"role": "user", "content": transcript})
    conversation_history.append({"role": "assistant", "content": response_text})
    
    audio_b64 = None
    
    return {
        "transcript": transcript,
        "response": response_text,
        "audio": audio_b64,
        "order": order_state.to_dict(),
        "timings": timings
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
