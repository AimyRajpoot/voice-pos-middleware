import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "db", "pizza_plaza.sqlite")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    base_price REAL NOT NULL,
    size_options TEXT NOT NULL,
    toppings TEXT NOT NULL,
    veg_flag BOOLEAN NOT NULL DEFAULT 0,
    stock_qty INTEGER NOT NULL DEFAULT 10
)
""")

products = [
    ("PIZ001", "Margherita Classic", 12.99,
     json.dumps([{"size": "small", "price_delta": -2.00}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 3.50}]),
     json.dumps([{"name": "fresh basil", "price": 0.0}, {"name": "extra mozzarella", "price": 1.50}, {"name": "garlic crust", "price": 1.00}]),
     True, 25),
    ("PIZ002", "Pepperoni Supreme", 14.99,
     json.dumps([{"size": "small", "price_delta": -2.50}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 4.00}]),
     json.dumps([{"name": "extra pepperoni", "price": 2.00}, {"name": "jalapenos", "price": 0.75}, {"name": "extra cheese", "price": 1.50}]),
     False, 20),
    ("PIZ003", "Veggie Deluxe", 13.99,
     json.dumps([{"size": "small", "price_delta": -2.00}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 3.50}]),
     json.dumps([{"name": "mushrooms", "price": 1.00}, {"name": "bell peppers", "price": 1.00}, {"name": "olives", "price": 0.75}, {"name": "onions", "price": 0.50}]),
     True, 18),
    ("PIZ004", "Meat Lovers", 16.99,
     json.dumps([{"size": "small", "price_delta": -3.00}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 4.50}]),
     json.dumps([{"name": "extra bacon", "price": 2.50}, {"name": "ham", "price": 1.50}, {"name": "sausage", "price": 1.50}]),
     False, 15),
    ("PIZ005", "BBQ Chicken", 15.49,
     json.dumps([{"size": "small", "price_delta": -2.50}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 4.00}]),
     json.dumps([{"name": "extra chicken", "price": 2.00}, {"name": "red onions", "price": 0.75}, {"name": "cilantro", "price": 0.50}]),
     False, 12),
    ("PIZ006", "Hawaiian Dream", 14.49,
     json.dumps([{"size": "small", "price_delta": -2.00}, {"size": "medium", "price_delta": 0.0}, {"size": "large", "price_delta": 3.50}]),
     json.dumps([{"name": "extra pineapple", "price": 1.00}, {"name": "extra ham", "price": 1.50}, {"name": "bacon crumble", "price": 2.00}]),
     False, 14),
    ("SID001", "Garlic Breadsticks", 5.99,
     json.dumps([{"size": "regular", "price_delta": 0.0}, {"size": "loaded", "price_delta": 2.50}]),
     json.dumps([{"name": "cheese dip", "price": 1.00}, {"name": "marinara extra", "price": 0.75}]),
     True, 30),
    ("SID002", "Caesar Salad", 6.99,
     json.dumps([{"size": "regular", "price_delta": 0.0}, {"size": "large", "price_delta": 2.00}]),
     json.dumps([{"name": "grilled chicken", "price": 3.00}, {"name": "extra parmesan", "price": 0.75}]),
     True, 20),
    ("SID003", "Mozzarella Sticks", 7.49,
     json.dumps([{"size": "regular", "price_delta": 0.0}, {"size": "big portion", "price_delta": 3.00}]),
     json.dumps([{"name": "ranch dip", "price": 0.75}, {"name": "marinara extra", "price": 0.75}]),
     True, 25),
    ("BEV001", "Fresh Lemonade", 3.49,
     json.dumps([{"size": "regular", "price_delta": 0.0}, {"size": "large", "price_delta": 1.00}]),
     json.dumps([{"name": "strawberry flavor", "price": 0.50}, {"name": "mint leaves", "price": 0.25}]),
     True, 40),
    ("BEV002", "Italian Soda", 3.99,
     json.dumps([{"size": "regular", "price_delta": 0.0}, {"size": "large", "price_delta": 1.00}]),
     json.dumps([{"name": "raspberry", "price": 0.50}, {"name": "peach", "price": 0.50}, {"name": "lavender", "price": 0.75}]),
     True, 35),
    ("DES001", "Tiramisu", 6.99,
     json.dumps([{"size": "slice", "price_delta": 0.0}, {"size": "whole", "price_delta": 12.00}]),
     json.dumps([]),
     True, 10),
    ("DES002", "Gelato Cup", 4.99,
     json.dumps([{"size": "single scoop", "price_delta": 0.0}, {"size": "double scoop", "price_delta": 2.50}]),
     json.dumps([{"name": "chocolate chip", "price": 0.50}, {"name": "hazelnut", "price": 0.50}, {"name": "coconut", "price": 0.50}]),
     True, 15),
]

cursor.executemany(
    """INSERT OR REPLACE INTO products 
    (sku, title, base_price, size_options, toppings, veg_flag, stock_qty) 
    VALUES (?, ?, ?, ?, ?, ?, ?)""",
    products
)

conn.commit()
conn.close()

print(f"Pizza Plaza database seeded successfully at {DB_PATH}")