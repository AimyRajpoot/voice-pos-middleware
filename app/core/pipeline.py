import os
import json
import re
import google.generativeai as genai

GENAI_KEY = os.getenv("GEMINI_API_KEY", "")
if GENAI_KEY:
    genai.configure(api_key=GENAI_KEY)

# Single source of truth for menu vocabulary (used by Whisper biasing, LLM prompt, and fallback parser)
MENU_VOCAB = [
    "zinger burger",
    "single burger", 
    "double burger",
    "coca-cola zero",
    "fries",
    "peppy"
]

MENU_VOCAB_STR = ", ".join(item.title() for item in MENU_VOCAB)  # For Whisper initial_prompt


async def get_menu_vocab_str(pos_adapter) -> str:
    """
    Dynamically fetch menu from POS adapter and return comma-separated string
    for Whisper initial_prompt. Falls back to static MENU_VOCAB_STR on error.
    """
    try:
        products = await pos_adapter.fetch_products()
        if products:
            return ", ".join(p["name"] for p in products)
    except Exception:
        pass
    return MENU_VOCAB_STR


class VoicePOSPipeline:
    def __init__(self, pos_adapter):
        self.pos_adapter = pos_adapter

    async def process_voice_text(self, text: str):
        parsed_llm = await self._parse_with_llm(text)
        return await self.pos_adapter.execute_order(parsed_llm)

    async def _parse_with_llm(self, text: str):
        menu_items = MENU_VOCAB
        
        # Build dynamic menu string for LLM
        menu_str = ", ".join(item.title() for item in menu_items)
        
        prompt = f"""
        You are an intelligent Fast-Food POS Voice Assistant for DukaanMind.
        
        STRICT VENDOR GUARDRAILS:
        - Available Menu Items ONLY: {menu_str}
        - If customer requests ANY item NOT in this exact list (e.g., "pizza", "mobile phone", "biryani", "burger king"), 
          you MUST return status: "OUT_OF_SCOPE" and politely inform them of available items.
        - Do NOT hallucinate or invent menu items.
        
        Customer Spoke: "{text}"

        Task:
        1. Parse intended menu items and exact quantities from customer speech.
        2. Correct common speech mishearings to valid menu items:
           - "in bed", "zing", "finger", "worker", "singing" -> "zinger burger"
           - "cook", "coke", "cola", "zero" -> "coca-cola zero"
           - "single" -> "single burger"
           - "double" -> "double burger"
        3. Map spoken numbers cleanly to quantities (e.g., "two", "2", "a couple" -> 2).
        4. If customer asks for items NOT on the menu, set status: "OUT_OF_SCOPE".
        5. Return ONLY valid JSON:
        {{
          "status": "success" | "OUT_OF_SCOPE",
          "reply": "I heard: 2 Zinger Burgers ($11.98). Would you like to confirm?",
          "items": [
             {{"name": "zinger burger", "quantity": 2}},
             {{"name": "coca-cola zero", "quantity": 1}}
          ]
        }}
        NOTE: The "reply" field should be a friendly confirmation message showing items, prices, and asking for confirmation.
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

        # Check off-menu items - any item not in MENU_VOCAB
        menu_items_lower = [item.lower() for item in MENU_VOCAB]
        # Common off-menu keywords to catch explicitly
        unsupported_keywords = ["biryani", "pizza", "pasta", "sushi", "taco", "ice cream", "mobile phone", "burger king", "mcdonalds", "kfc"]
        if any(unsupported in text_lower for unsupported in unsupported_keywords):
            menu_list = ", ".join(item.title() for item in MENU_VOCAB)
            return {
                "status": "OUT_OF_SCOPE",
                "reply": f"I'm sorry, we don't serve that here! We offer {menu_list}.",
                "items": []
            }

        # Check for specific burger types first (more specific matches)
        # Double Burger
        if "double burger" in text_lower or "double" in text_lower:
            qty = 2 if any(q in text_lower for q in ["two double", "2 double"]) else 1
            items.append({"name": "double burger", "quantity": qty})
        
        # Single Burger
        elif "single burger" in text_lower or "single" in text_lower:
            qty = 2 if any(q in text_lower for q in ["two single", "2 single"]) else 1
            items.append({"name": "single burger", "quantity": qty})
        
        # Phonetic matching for Zinger Burger (handles "in bed", "zing", "finger", "singing", etc.)
        # Only match if not already matched as single/double burger
        zinger_triggers = ["zinger", "zing", "in bed", "bed", "finger", "worker", "singing"]
        if any(w in text_lower for w in zinger_triggers) and "single" not in text_lower and "double" not in text_lower:
            # Check for quantity 2
            qty = 2 if any(q in text_lower for q in ["two zinger", "2 zinger", "two burger", "2 burger"]) else 1
            items.append({"name": "zinger burger", "quantity": qty})

        # Matching for Coke / Drink
        coke_triggers = ["coke", "coca", "zero", "drink", "cola", "cke"]
        if any(w in text_lower for w in coke_triggers):
            qty = 2 if any(q in text_lower for q in ["two coke", "2 coke", "two zero", "2 zero"]) else 1
            items.append({"name": "coca-cola zero", "quantity": qty})

        # Matching for Fries
        if "fries" in text_lower or "fry" in text_lower:
            qty = 2 if any(q in text_lower for q in ["two fries", "2 fries"]) else 1
            items.append({"name": "fries", "quantity": qty})

        # Matching for Peppy
        if "peppy" in text_lower:
            qty = 2 if any(q in text_lower for q in ["two peppy", "2 peppy"]) else 1
            items.append({"name": "peppy", "quantity": qty})

        return {
            "status": "success",
            "reply": "I heard: " + ", ".join(f"{item['quantity']} {item['name'].title()}" for item in items) + ". Would you like to confirm?",
            "items": items
        }
