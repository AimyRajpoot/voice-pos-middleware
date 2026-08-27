from abc import ABC, abstractmethod
from typing import Any


class BasePOSAdapter(ABC):

    @abstractmethod
    async def fetch_products(self) -> list[dict[str, Any]]:
        """
        Get the product/menu list from the POS.
        """
        pass

    @abstractmethod
    async def get_product(self, product_id: str) -> dict[str, Any]:
        """
        Get information about one product.
        """
        pass

    @abstractmethod
    async def get_stock(self, product_id: str) -> dict[str, Any]:
        """
        Get current stock for a product.
        """
        pass

    @abstractmethod
    async def create_order(
        self,
        items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Create an order in the POS.
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any]:
        """
        Get an existing order from the POS.
        """
        pass