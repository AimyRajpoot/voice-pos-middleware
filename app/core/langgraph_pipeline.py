"""
LangGraph State Machine for Voice POS Pipeline.

Implements a 4-node workflow:
1. intent_classifier  -> [ORDER, MENU_QA, OUT_OF_SCOPE]
2. inventory_validator -> validates stock, routes off-menu to OUT_OF_SCOPE
3. confirmation_node   -> generates store-oriented confirmation
4. order_executor      -> finalizes stock deduction & receipt JSON
"""

import os
import json
from typing import Literal, TypedDict
from enum import Enum

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.adapters.mock_pos import MockPOSAdapter
from app.core.pipeline import MENU_VOCAB, MENU_VOCAB_STR, get_menu_vocab_str

# Optional LangSmith tracing
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "voice-pos-middleware")

if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT


class IntentType(str, Enum):
    ORDER = "ORDER"
    MENU_QA = "MENU_QA"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class PipelineState(TypedDict):
    """State schema for the Voice POS workflow."""
    transcript: str
    intent: IntentType | None
    parsed_items: list[dict] | None
    validated_items: list[dict] | None
    unavailable_items: list[str] | None
    confirmation_message: str | None
    user_confirmed: bool | None
    receipt: dict | None
    error: str | None


def get_llm():
    """Initialize LLM with JSON output mode."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=0,
        response_format={"type": "json_object"},
    )
# ──────────────────────────────────────────────────────────────────────────────
# NODE 1: INTENT CLASSIFIER
# ──────────────────────────────────────────────────────────────────────────────
INTENT_CLASSIFIER_PROMPT = f"""You are an intent classifier for a fast-food Voice POS system.

Available Menu Items: {MENU_VOCAB_STR}

Classify the user's speech into ONE of these categories:
- ORDER: User wants to place an order (mentions quantities + menu items)
- MENU_QA: User asks questions about menu (ingredients, price, stock, allergens, options)
- OUT_OF_SCOPE: User asks for items NOT on menu, or completely unrelated topics

Return ONLY valid JSON:
{{
  "intent": "ORDER" | "MENU_QA" | "OUT_OF_SCOPE",
  "reasoning": "Brief explanation"
}}"""


async def intent_classifier(state: PipelineState) -> PipelineState:
    """Classify transcript into ORDER, MENU_QA, or OUT_OF_SCOPE."""
    transcript = state["transcript"]
    llm = get_llm()
    
    if not llm:
        # Fallback: simple keyword-based classification
        text_lower = transcript.lower()
        order_keywords = ["order", "want", "get", "give me", "i'll have", "i would like", "can i have"]
        qa_keywords = ["what", "how much", "price", "cost", "ingredients", "allergen", "vegetarian", "vegan", "stock", "available", "do you have", "what's in", "does the"]
        
        # Check for explicit off-menu items first
        off_menu_keywords = ["pizza", "biryani", "pasta", "sushi", "taco", "ice cream", "burger king", "mcdonald", "kfc"]
        if any(kw in text_lower for kw in off_menu_keywords):
            intent = IntentType.OUT_OF_SCOPE
        elif any(kw in text_lower for kw in qa_keywords):
            intent = IntentType.MENU_QA
        elif any(kw in text_lower for kw in order_keywords):
            # Has order intent keywords - let validator handle parsing (including phonetic matching)
            intent = IntentType.ORDER
        else:
            # Check if mentioning menu items at all (exact or phonetic)
            if any(item in text_lower for item in MENU_VOCAB):
                intent = IntentType.ORDER
            else:
                # Default to ORDER if unclear but has food-like words, let validator decide
                food_like = ["burger", "fries", "drink", "coke", "soda", "peppy", "chicken", "sandwich"]
                if any(w in text_lower for w in food_like):
                    intent = IntentType.ORDER
                else:
                    intent = IntentType.OUT_OF_SCOPE
    else:
        prompt = INTENT_CLASSIFIER_PROMPT + f"\n\nUser said: \"{transcript}\""
        try:
            response = await llm.ainvoke(prompt)
            result = json.loads(response.content)
            intent = IntentType(result["intent"])
        except Exception:
            text_lower = transcript.lower()
            off_menu_keywords = ["pizza", "biryani", "pasta", "sushi", "taco", "ice cream"]
            if any(kw in text_lower for kw in off_menu_keywords):
                intent = IntentType.OUT_OF_SCOPE
            elif any(item in transcript.lower() for item in MENU_VOCAB):
                intent = IntentType.ORDER
            else:
                # Default to ORDER for ambiguous food requests, let validator handle
                food_like = ["burger", "fries", "drink", "coke", "soda", "peppy", "chicken", "sandwich"]
                if any(w in text_lower for w in food_like):
                    intent = IntentType.ORDER
                else:
                    intent = IntentType.OUT_OF_SCOPE
    
    return {**state, "intent": intent}
# ──────────────────────────────────────────────────────────────────────────────
# NODE 2: INVENTORY VALIDATOR
# ──────────────────────────────────────────────────────────────────────────────
ORDER_PARSER_PROMPT = f"""You are a precise order parser for a fast-food POS.

Available Menu Items: {MENU_VOCAB_STR}

Parse the user's speech into structured items with quantities.
Correct speech mishearings (e.g., 'in bed' -> 'zinger burger', 'singing' -> 'zinger burger', 'cook' -> 'coke').

Return ONLY valid JSON:
{{
  "items": [
    {{"name": "zinger burger", "quantity": 2}},
    {{"name": "fries", "quantity": 1}}
  ]
}}

If NO valid menu items found, return {{"items": []}}"""


async def inventory_validator(state: PipelineState) -> PipelineState:
    """Parse order items and validate against live inventory."""
    if state["intent"] != IntentType.ORDER:
        return {**state, "parsed_items": [], "validated_items": [], "unavailable_items": []}
    
    transcript = state["transcript"]
    adapter = MockPOSAdapter()
    llm = get_llm()
    
    # Try LLM first, then fallback parser
    parsed_items = []
    if llm:
        try:
            prompt = ORDER_PARSER_PROMPT + f"\n\nUser said: \"{transcript}\""
            response = await llm.ainvoke(prompt)
            parsed = json.loads(response.content)
            parsed_items = parsed.get("items", [])
        except Exception:
            parsed_items = []
    
    # If LLM fails or returns empty, use fallback parser
    if not parsed_items:
        from app.core.pipeline import VoicePOSPipeline as LegacyPipeline
        legacy = LegacyPipeline(adapter)
        result = await legacy._parse_with_llm(transcript)
        parsed_items = result.get("items", [])
    
    validated_items = []
    unavailable_items = []
    
    for item in parsed_items:
        name = item.get("name", "").lower().strip()
        qty = item.get("quantity", 1)
        
        if name in adapter.inventory:
            stock = adapter.inventory[name]["stock"]
            price = adapter.inventory[name]["price"]
            
            if stock >= qty:
                validated_items.append({
                    "name": name,
                    "quantity": qty,
                    "unit_price": price,
                    "subtotal": round(price * qty, 2)
                })
            else:
                unavailable_items.append(f"{name.title()} (Only {stock} in stock)")
        else:
            unavailable_items.append(f"{name.title()} (Not on menu)")
    
    # Even if all items unavailable, still go to confirmation to show what was unavailable
    return {
        **state,
        "parsed_items": parsed_items,
        "validated_items": validated_items,
        "unavailable_items": unavailable_items
    }


# ──────────────────────────────────────────────────────────────────────────────
# NODE 3: CONFIRMATION NODE
# ──────────────────────────────────────────────────────────────────────────────
def confirmation_node(state: PipelineState) -> PipelineState:
    """Generate store-oriented confirmation message."""
    validated = state.get("validated_items", [])
    unavailable = state.get("unavailable_items", [])
    
    # Check if auto-confirmation mode (user_confirmed is already True)
    auto_confirm = state.get("user_confirmed") is True
    
    if not validated and not unavailable:
        return {
            **state,
            "confirmation_message": "I didn't catch any valid menu items. Could you please repeat your order?",
            "user_confirmed": False
        }
    
    lines = ["I heard:"]
    subtotal = 0
    
    for item in validated:
        line = f"  {item['quantity']}x {item['name'].title()} @ ${item['unit_price']:.2f} = ${item['subtotal']:.2f}"
        lines.append(line)
        subtotal += item['subtotal']
    
    tax = round(subtotal * 0.05, 2)
    total = round(subtotal + tax, 2)
    
    lines.append(f"\nSubtotal: ${subtotal:.2f}")
    lines.append(f"Tax (5%): ${tax:.2f}")
    lines.append(f"Total: ${total:.2f}")
    
    if unavailable:
        lines.append("\nUnavailable:")
        for u in unavailable:
            lines.append(f"  - {u}")
    
    if auto_confirm:
        lines.append("\n[Auto-confirmed for API compatibility]")
        return {
            **state,
            "confirmation_message": "\n".join(lines),
            "user_confirmed": True
        }
    
    lines.append("\nShould I confirm this order?")
    
    return {
        **state,
        "confirmation_message": "\n".join(lines),
        "user_confirmed": None
    }


# ──────────────────────────────────────────────────────────────────────────────
# NODE 4: ORDER EXECUTOR
# ──────────────────────────────────────────────────────────────────────────────
async def order_executor(state: PipelineState) -> PipelineState:
    """Execute confirmed order: deduct stock, generate receipt."""
    if not state.get("user_confirmed"):
        return {
            **state,
            "receipt": {
                "status": "cancelled",
                "message": "Order cancelled - not confirmed by user."
            }
        }
    
    validated = state.get("validated_items", [])
    unavailable = state.get("unavailable_items", [])
    adapter = MockPOSAdapter()
    
    if not validated:
        return {
            **state,
            "receipt": {
                "status": "unsupported",
                "message": "No valid items to order.",
                "items": [],
                "unavailable": unavailable,
                "total_amount": 0.0
            }
        }
    
    receipt_items = []
    total = 0.0
    
    for item in validated:
        name = item["name"]
        qty = item["quantity"]
        
        adapter.inventory[name]["stock"] -= qty
        
        receipt_items.append({
            "name": name.title(),
            "quantity": qty,
            "unit_price": item["unit_price"],
            "subtotal": item["subtotal"]
        })
        total += item["subtotal"]
    
    return {
        **state,
        "receipt": {
            "status": "success",
            "order_id": f"ORD-{hash(str(validated)) % 10000}",
            "items": receipt_items,
            "unavailable": unavailable if unavailable else None,
            "total_amount": round(total, 2),
            "assistant_note": "Order confirmed and processed successfully!"
        }
    }
# ──────────────────────────────────────────────────────────────────────────────
# ROUTING LOGIC
# ──────────────────────────────────────────────────────────────────────────────
def route_after_classifier(state: PipelineState) -> Literal["inventory_validator", "menu_qa_handler", "out_of_scope_handler"]:
    """Route based on classified intent."""
    intent = state.get("intent")
    if intent == IntentType.ORDER:
        return "inventory_validator"
    elif intent == IntentType.MENU_QA:
        return "menu_qa_handler"
    return "out_of_scope_handler"


def route_after_validator(state: PipelineState) -> Literal["confirmation_node", "out_of_scope_handler"]:
    """Route after inventory validation."""
    validated = state.get("validated_items", [])
    unavailable = state.get("unavailable_items", [])
    parsed = state.get("parsed_items", [])
    
    # If no items were even parsed (completely unrecognized), treat as out of scope
    if not parsed:
        return "out_of_scope_handler"
    
    # Otherwise go to confirmation (shows both validated and unavailable)
    return "confirmation_node"


def route_after_confirmation(state: PipelineState) -> Literal["order_executor", "end"]:
    """Route after confirmation - in real app, this waits for user input."""
    return "order_executor"


async def menu_qa_handler(state: PipelineState) -> PipelineState:
    """Handle menu Q&A queries using RAG."""
    from app.core.rag_engine import get_rag_engine
    
    rag = get_rag_engine()
    result = await rag.query(state["transcript"])
    
    answer = result.get("answer", "I'm not sure about that. Please ask about our menu items.")
    citations = result.get("citations", [])
    
    return {
        **state,
        "receipt": {
            "status": "menu_qa",
            "message": answer,
            "citations": citations,
            "items": [],
            "total_amount": 0.0
        }
    }


async def out_of_scope_handler(state: PipelineState) -> PipelineState:
    """Handle out-of-scope requests."""
    return {
        **state,
        "receipt": {
            "status": "unsupported",
            "message": "I'm sorry, we don't serve that here! We offer Zinger Burgers, Single/Double Burgers, Fries, Coca-Cola Zero, and Peppy.",
            "items": [],
            "total_amount": 0.0
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ──────────────────────────────────────────────────────────────────────────────
def build_graph():
    """Construct and compile the LangGraph StateGraph."""
    workflow = StateGraph(PipelineState)
    
    # Add nodes
    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("inventory_validator", inventory_validator)
    workflow.add_node("confirmation_node", confirmation_node)
    workflow.add_node("order_executor", order_executor)
    workflow.add_node("menu_qa_handler", menu_qa_handler)
    workflow.add_node("out_of_scope_handler", out_of_scope_handler)
    
    # Edges
    workflow.add_edge(START, "intent_classifier")
    
    workflow.add_conditional_edges(
        "intent_classifier",
        route_after_classifier,
        {
            "inventory_validator": "inventory_validator",
            "menu_qa_handler": "menu_qa_handler",
            "out_of_scope_handler": "out_of_scope_handler",
        }
    )
    
    workflow.add_conditional_edges(
        "inventory_validator",
        route_after_validator,
        {
            "confirmation_node": "confirmation_node",
            "out_of_scope_handler": "out_of_scope_handler",
        }
    )
    
    workflow.add_conditional_edges(
        "confirmation_node",
        route_after_confirmation,
        {
            "order_executor": "order_executor",
            "end": END,
        }
    )
    
    workflow.add_edge("order_executor", END)
    workflow.add_edge("menu_qa_handler", END)
    workflow.add_edge("out_of_scope_handler", END)
    
    # Compile with memory checkpoint for LangSmith tracing
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE (compatible with existing VoicePOSPipeline)
# ──────────────────────────────────────────────────────────────────────────────
class LangGraphVoicePOSPipeline:
    """LangGraph-backed pipeline matching VoicePOSPipeline interface."""
    
    def __init__(self, pos_adapter: MockPOSAdapter):
        self.pos_adapter = pos_adapter
        self.graph = build_graph()
        self.config = {"configurable": {"thread_id": "voice-pos-session"}}
    
    async def process_voice_text(self, text: str) -> dict:
        """Process transcript through LangGraph workflow."""
        initial_state = {
            "transcript": text,
            "intent": None,
            "parsed_items": None,
            "validated_items": None,
            "unavailable_items": None,
            "confirmation_message": None,
            "user_confirmed": True,  # Auto-confirm for API compatibility
            "receipt": None,
            "error": None,
        }
        
        final_state = await self.graph.ainvoke(initial_state, config=self.config)
        return final_state.get("receipt", {
            "status": "error",
            "message": "Pipeline execution failed",
            "items": [],
            "total_amount": 0.0
        })


# Backwards-compatible alias
VoicePOSPipeline = LangGraphVoicePOSPipeline