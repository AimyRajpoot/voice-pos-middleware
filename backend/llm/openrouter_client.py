import os
import json
import re
from typing import Optional, Dict, Any, Tuple
import openai

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are a friendly voice ordering assistant for a restaurant.

When the customer wants to order something, you MUST respond with:
1. A friendly confirmation message
2. At the end, include a special action tag in brackets like: [ADD: Classic Burger x1] or [ADD: Cheese Burger x2]
3. If removing an item from the cart, tell them which item and use: [REMOVE: 1] (use the item number from the current order list)

Example responses:
- "I've added a Classic Burger to your order for $8.99. [ADD: Classic Burger x1]"
- "Two Cheese Burgers coming up! [ADD: Cheese Burger x2]"
- "I see you want the Spicy Burger. [ADD: Spicy Burger x1]"
- "I've removed item 1 from your order. [REMOVE: 1]"

Always use item names exactly as they appear on the menu. Include price in your response.
"""


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=OPENROUTER_BASE_URL)

    def parse_actions(self, response: str) -> list[Tuple[str, str, int]]:
        """Parse [ADD: Item x2] or [REMOVE: 1] tags from response."""
        actions = []
        add_pattern = r'\[ADD:\s*(.+?)\s*x\s*(\d+)\s*\]'
        for match in re.finditer(add_pattern, response, re.IGNORECASE):
            item_name = match.group(1).strip()
            qty = int(match.group(2))
            actions.append(('add', item_name, qty))
        
        remove_pattern = r'\[REMOVE:\s*(\d+)\s*\]'
        for match in re.finditer(remove_pattern, response, re.IGNORECASE):
            idx = int(match.group(1)) - 1  # Convert to 0-based index
            actions.append(('remove', '', idx))
        
        return actions

    def simple_chat(self, user_message: str, menu_context: str, order_context: str, conversation_history: list[dict] = None) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append({"role": "system", "content": f"Menu:\n{menu_context}"})
        messages.append({"role": "system", "content": order_context})
        
        if conversation_history:
            messages.extend(conversation_history[-6:])
        
        messages.append({"role": "user", "content": user_message})
        
        response = self.client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages
        )
        
        return response.choices[0].message.content or ""
