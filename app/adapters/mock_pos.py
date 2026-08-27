from app.adapters.base import BasePOSAdapter
from typing import Any

class MockPOSAdapter(BasePOSAdapter):
    def __init__(self):
        # Database with item prices and live stock levels
        self.inventory = {
            "zinger burger": {"price": 5.99, "stock": 10},
            "single burger": {"price": 4.50, "stock": 5},
            "double burger": {"price": 6.50, "stock": 0},  # Out of stock example
            "coca-cola zero": {"price": 1.99, "stock": 15},
            "fries": {"price": 2.50, "stock": 20},
            "peppy": {"price": 1.99, "stock": 100}
        }

    async def fetch_products(self) -> list[dict[str, Any]]:
        """Get the product/menu list from the POS."""
        return [
            {"id": "101", "name": "Zinger Burger", "price": 5.99, "stock": 10, "category": "Burgers"},
            {"id": "102", "name": "Single Burger", "price": 4.50, "stock": 5, "category": "Burgers"},
            {"id": "103", "name": "Double Burger", "price": 6.50, "stock": 0, "category": "Burgers"},
            {"id": "104", "name": "Coca-Cola Zero", "price": 1.99, "stock": 15, "category": "Drinks"},
            {"id": "105", "name": "Fries", "price": 2.50, "stock": 20, "category": "Sides"},
            {"id": "106", "name": "Peppy", "price": 1.99, "stock": 100, "category": "Drinks"}
        ]

    async def get_product(self, product_id: str) -> dict[str, Any]:
        """Get information about one product."""
        products = await self.fetch_products()
        for product in products:
            if product["id"] == product_id:
                return product
        raise ValueError(f"Product {product_id} not found")

    async def get_stock(self, product_id: str) -> dict[str, Any]:
        """Get current stock for a product."""
        product = await self.get_product(product_id)
        return {
            "product_id": product_id,
            "product_name": product["name"],
            "stock": product["stock"]
        }

    async def create_order(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Create an order in the POS."""
        total = 0.0
        order_items = []

        for item in items:
            product_id = item.get("product_id")
            qty = item.get("quantity", 1)
            product = await self.get_product(product_id)
            
            if qty > product["stock"]:
                raise ValueError(f"Only {product['stock']} units of {product['name']} are available")
            
            item_total = product["price"] * qty
            total += item_total
            order_items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": qty,
                "unit_price": product["price"],
                "total": item_total
            })

        # Reduce stock
        for item in items:
            product_id = item.get("product_id")
            qty = item.get("quantity", 1)
            product = await self.get_product(product_id)
            product["stock"] -= qty

        return {
            "order_id": f"ORD-{hash(str(items)) % 10000}",
            "items": order_items,
            "total": round(total, 2),
            "status": "created"
        }

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Get an existing order from the POS."""
        # Mock implementation - in real POS this would query the database
        return {"order_id": order_id, "status": "not_found"}

    async def execute_order(self, parsed_data: dict):
        # Handle both "unsupported" (legacy) and "OUT_OF_SCOPE" (new) statuses
        if parsed_data.get("status") in ("unsupported", "OUT_OF_SCOPE"):
            return {
                "status": "unsupported",
                "message": parsed_data.get("reply", "Sorry, we don't serve that item here.")
            }

        items_requested = parsed_data.get("items", [])
        processed_items = []
        unavailable_items = []
        total = 0.0

        for item in items_requested:
            name = item.get("name", "").lower().strip()
            qty = item.get("quantity", 1)

            if name in self.inventory:
                stock_available = self.inventory[name]["stock"]
                price = self.inventory[name]["price"]

                if stock_available >= qty:
                    subtotal = price * qty
                    total += subtotal
                    processed_items.append({
                        "name": name.title(),
                        "quantity": qty,
                        "unit_price": price,
                        "subtotal": round(subtotal, 2)
                    })
                else:
                    unavailable_items.append(f"{name.title()} (Only {stock_available} in stock)")
            else:
                unavailable_items.append(f"{name.title()} (Not on menu)")

        return {
            "status": "success",
            "order_id": "ORD-8821",
            "items": processed_items,
            "unavailable": unavailable_items,
            "total_amount": round(total, 2),
            "assistant_note": parsed_data.get("reply", "Order processed successfully!")
        }
