from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizedModifier:
    name: str
    extra_price: float


@dataclass
class NormalizedItem:
    id: str
    name: str
    category: str
    price: float
    in_stock: bool
    stock_qty: int = 0
    modifiers: list[NormalizedModifier] = field(default_factory=list)


class BusinessAdapter(ABC):
    @abstractmethod
    def get_menu(self) -> list[NormalizedItem]:
        pass

    @abstractmethod
    def get_item(self, name: str) -> Optional[NormalizedItem]:
        pass

    @abstractmethod
    def check_stock(self, name: str) -> bool:
        pass

    @abstractmethod
    def get_modifiers(self, item_name: str) -> list[NormalizedModifier]:
        pass

    @abstractmethod
    def update_stock(self, item_id: str, quantity: int) -> bool:
        pass

    @abstractmethod
    def restore_stock(self, item_id: str, quantity: int) -> bool:
        pass
