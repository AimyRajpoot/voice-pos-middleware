import sqlite3
import os
from typing import Optional
from .base import BusinessAdapter, NormalizedItem, NormalizedModifier


class BurgerBarnAdapter(BusinessAdapter):
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(backend_dir, "db", "burger_barn.sqlite")
        self.db_path = db_path
        self._ensure_stock_column()

    def _ensure_stock_column(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(items)")
        columns = [col[1] for col in cursor.fetchall()]
        if "stock_qty" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN stock_qty INTEGER DEFAULT 10")
            conn.commit()
        conn.close()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_menu(self) -> list[NormalizedItem]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, price, stock_qty FROM items")
        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            item_id, name, category, price, stock_qty = row
            modifiers = self.get_modifiers(name)
            items.append(NormalizedItem(
                id=str(item_id),
                name=name,
                category=category,
                price=price,
                in_stock=stock_qty > 0,
                stock_qty=stock_qty,
                modifiers=modifiers
            ))
        return items

    def get_item(self, name: str) -> Optional[NormalizedItem]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, category, price, stock_qty FROM items WHERE LOWER(name) LIKE LOWER(?)",
            ("%" + name + "%",)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        item_id, name, category, price, stock_qty = row
        modifiers = self.get_modifiers(name)
        return NormalizedItem(
            id=str(item_id),
            name=name,
            category=category,
            price=price,
            in_stock=stock_qty > 0,
            stock_qty=stock_qty,
            modifiers=modifiers
        )

    def check_stock(self, name: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stock_qty FROM items WHERE LOWER(name) LIKE LOWER(?)",
            ("%" + name + "%",)
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row[0] > 0) if row else False

    def update_stock(self, item_id: str, quantity: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE items SET stock_qty = stock_qty - ? WHERE id = ? AND stock_qty >= ?",
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
            "UPDATE items SET stock_qty = stock_qty + ? WHERE id = ?",
            (quantity, item_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_modifiers(self, item_name: str) -> list[NormalizedModifier]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.name, m.extra_price 
            FROM modifiers m
            JOIN items i ON m.item_id = i.id
            WHERE LOWER(i.name) LIKE LOWER(?)
        """, ("%" + item_name + "%",))
        rows = cursor.fetchall()
        conn.close()
        return [NormalizedModifier(name=name, extra_price=price) for name, price in rows]
