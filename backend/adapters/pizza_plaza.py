import sqlite3
import json
import os
from typing import Optional
from .base import BusinessAdapter, NormalizedItem, NormalizedModifier


class PizzaPlazaAdapter(BusinessAdapter):
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "db", "pizza_plaza.sqlite")
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_menu(self) -> list[NormalizedItem]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sku, title, base_price, size_options, toppings, veg_flag, stock_qty FROM products")
        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            sku, title, base_price, size_options_json, toppings_json, veg_flag, stock_qty = row
            size_options = json.loads(size_options_json)
            toppings = json.loads(toppings_json)
            
            modifiers = []
            for s in size_options:
                modifiers.append(NormalizedModifier(
                    name=s["size"] + " size",
                    extra_price=s["price_delta"]
                ))
            for t in toppings:
                modifiers.append(NormalizedModifier(
                    name="add " + t["name"],
                    extra_price=t["price"]
                ))
            
            category = "pizza"
            title_lower = title.lower()
            if "salad" in title_lower or "sticks" in title_lower or "bread" in title_lower:
                category = "side"
            elif "lemonade" in title_lower or "soda" in title_lower:
                category = "drink"
            elif "tiramisu" in title_lower or "gelato" in title_lower:
                category = "dessert"

            items.append(NormalizedItem(
                id=sku,
                name=title,
                category=category,
                price=base_price,
                in_stock=stock_qty > 0,
                stock_qty=stock_qty,
                modifiers=modifiers
            ))
        return items

    def get_item(self, name: str) -> Optional[NormalizedItem]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sku, title, base_price, size_options, toppings, veg_flag, stock_qty FROM products WHERE LOWER(title) LIKE LOWER(?)",
            ("%" + name + "%",)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        sku, title, base_price, size_options_json, toppings_json, veg_flag, stock_qty = row
        size_options = json.loads(size_options_json)
        toppings = json.loads(toppings_json)

        modifiers = []
        for s in size_options:
            modifiers.append(NormalizedModifier(
                name=s["size"] + " size",
                extra_price=s["price_delta"]
            ))
        for t in toppings:
            modifiers.append(NormalizedModifier(
                name="add " + t["name"],
                extra_price=t["price"]
            ))

        category = "pizza"
        title_lower = title.lower()
        if "salad" in title_lower or "sticks" in title_lower or "bread" in title_lower:
            category = "side"
        elif "lemonade" in title_lower or "soda" in title_lower:
            category = "drink"
        elif "tiramisu" in title_lower or "gelato" in title_lower:
            category = "dessert"

        return NormalizedItem(
            id=sku,
            name=title,
            category=category,
            price=base_price,
            in_stock=stock_qty > 0,
            stock_qty=stock_qty,
            modifiers=modifiers
        )

    def check_stock(self, name: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stock_qty FROM products WHERE LOWER(title) LIKE LOWER(?)",
            ("%" + name + "%",)
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row[0] > 0) if row else False

    def update_stock(self, item_id: str, quantity: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET stock_qty = stock_qty - ? WHERE sku = ? AND stock_qty >= ?",
            (quantity, item_id, quantity)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def restore_stock(self, item_id: str, quantity: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET stock_qty = stock_qty + ? WHERE sku = ?",
            (quantity, item_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_modifiers(self, item_name: str) -> list[NormalizedModifier]:
        item = self.get_item(item_name)
        return item.modifiers if item else []
