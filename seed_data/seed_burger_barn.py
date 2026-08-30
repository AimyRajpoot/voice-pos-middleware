import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "db")
DB_PATH = os.path.join(DB_DIR, "burger_barn.sqlite")

os.makedirs(DB_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    is_combo BOOLEAN NOT NULL DEFAULT 0,
    spice_level TEXT NOT NULL DEFAULT 'mild',
    stock_qty INTEGER NOT NULL DEFAULT 10
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS modifiers (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    extra_price REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (item_id) REFERENCES items(id)
)
""")

items = [
    ("Classic Burger", "burger", 8.99, False, "mild", 15),
    ("Cheese Burger", "burger", 9.99, False, "mild", 12),
    ("Spicy Burger", "burger", 10.99, False, "hot", 10),
    ("Double Patty Burger", "burger", 12.99, False, "mild", 8),
    ("Bacon BBQ Burger", "burger", 11.99, False, "medium", 10),
    ("Veggie Burger", "burger", 9.49, False, "mild", 8),
    ("Chicken Burger", "burger", 9.49, False, "mild", 12),
    ("Crispy Fries", "side", 3.49, False, "mild", 25),
    ("Loaded Fries", "side", 5.99, False, "mild", 15),
    ("Onion Rings", "side", 4.49, False, "mild", 18),
    ("Garden Salad", "side", 5.49, False, "mild", 10),
    ("Cola", "drink", 2.49, False, "mild", 30),
    ("Lemonade", "drink", 2.99, False, "mild", 25),
    ("Milkshake", "drink", 4.99, False, "mild", 15),
    ("Iced Tea", "drink", 2.29, False, "mild", 20),
    ("Burger Combo", "combo", 13.99, True, "mild", 10),
    ("Kids Meal", "combo", 7.99, True, "mild", 8),
]

cursor.executemany(
    "INSERT OR REPLACE INTO items (name, category, price, is_combo, spice_level, stock_qty) VALUES (?, ?, ?, ?, ?, ?)",
    items
)

cursor.execute("SELECT id, name FROM items")
burger_items = cursor.fetchall()

modifiers = []
for item_id, item_name in burger_items:
    if "burger" in item_name.lower():
        modifiers.extend([
            (item_id, "no pickles", 0.0),
            (item_id, "extra cheese", 0.50),
            (item_id, "add bacon", 1.50),
            (item_id, "no onions", 0.0),
            (item_id, "extra sauce", 0.0),
        ])
    elif "fries" in item_name.lower() or "rings" in item_name.lower():
        modifiers.extend([
            (item_id, "large size", 1.00),
            (item_id, "extra crispy", 0.0),
        ])
    elif "drink" in item_name.lower() or "shake" in item_name.lower() or "tea" in item_name.lower():
        modifiers.extend([
            (item_id, "large size", 0.75),
            (item_id, "no ice", 0.0),
        ])

cursor.execute("DELETE FROM modifiers")
cursor.executemany(
    "INSERT INTO modifiers (item_id, name, extra_price) VALUES (?, ?, ?)",
    modifiers
)

conn.commit()
conn.close()

print(f"Burger Barn database seeded successfully at {DB_PATH}")
