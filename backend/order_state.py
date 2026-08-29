import os
from dataclasses import dataclass, field
from typing import Optional
from adapters import BusinessAdapter


@dataclass
class OrderItem:
    item_id: str
    name: str
    quantity: int
    price: float
    modifiers: list[str] = field(default_factory=list)


class OrderState:
    def __init__(self):
        self.items: list[OrderItem] = []
        self.current_business: str = "burger_barn"
        self.adapter: Optional[BusinessAdapter] = None

    def add_item(self, item_id: str, name: str, quantity: int, price: float, modifiers: list[str] = None):
        self.items.append(OrderItem(
            item_id=item_id,
            name=name,
            quantity=quantity,
            price=price,
            modifiers=modifiers or []
        ))

    def remove_item(self, index: int):
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def clear_order(self):
        self.items.clear()

    def get_total(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    def to_dict(self) -> dict:
        return {
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "modifiers": item.modifiers
                }
                for item in self.items
            ],
            "total": self.get_total(),
            "business": self.current_business
        }
