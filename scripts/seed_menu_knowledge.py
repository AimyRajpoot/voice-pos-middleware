#!/usr/bin/env python
"""
Seed LanceDB vector database with menu knowledge for RAG.
Run this script once after POS adapter is configured.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def seed_menu_knowledge():
    """Populate LanceDB with menu items from POS adapter."""
    import lancedb
    from sentence_transformers import SentenceTransformer
    from app.adapters.mock_pos import MockPOSAdapter
    from app.schemas.pos import ProductSchema
    
    print("=" * 60)
    print("DukaanMind - RAG Menu Knowledge Seeding")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Connecting to LanceDB...")
    db = lancedb.connect(".lancedb")
    
    print("2. Loading embedding model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("3. Fetching menu from POS adapter...")
    adapter = MockPOSAdapter()
    raw_products = await adapter.fetch_products()
    products = [ProductSchema(**p) for p in raw_products]
    print(f"   Found {len(products)} menu items")
    
    # Prepare documents for embedding
    print("\n4. Preparing documents for vector indexing...")
    documents = []
    
    for product in products:
        # Create rich text representation for each product
        text_parts = [
            f"Item: {product.name}",
            f"Category: {product.category or 'Uncategorized'}",
            f"Price: ${product.price:.2f}",
            f"Stock: {product.stock} units",
        ]
        
        # Add dietary/allergen info based on name (mock data)
        name_lower = product.name.lower()
        if "burger" in name_lower:
            text_parts.append("Type: Burger (contains gluten, meat)")
            if "zinger" in name_lower:
                text_parts.append("Spicy: Yes")
                text_parts.append("Description: Crispy chicken fillet with spicy sauce, lettuce, and mayo on a sesame bun")
            elif "double" in name_lower:
                text_parts.append("Description: Two beef patties with cheese, lettuce, tomato, onion, and special sauce")
            else:
                text_parts.append("Description: Single beef patty with cheese, lettuce, tomato, onion, and special sauce")
        elif "fries" in name_lower:
            text_parts.append("Type: Side (vegetarian, gluten-free)")
            text_parts.append("Description: Crispy golden french fries, lightly salted")
        elif "coca-cola" in name_lower or "coke" in name_lower:
            text_parts.append("Type: Drink (vegan, gluten-free)")
            text_parts.append("Description: Coca-Cola Zero Sugar, zero calories, zero sugar")
        
        if product.stock == 0:
            text_parts.append("Availability: OUT OF STOCK")
        elif product.stock < 5:
            text_parts.append(f"Availability: Low stock ({product.stock} left)")
        else:
            text_parts.append("Availability: In stock")
        
        full_text = "\n".join(text_parts)
        
        documents.append({
            "id": product.id,
            "text": full_text,
            "name": product.name,
            "category": product.category or "",
            "price": product.price,
            "stock": product.stock,
            "vector": embedder.encode(full_text).tolist()
        })
        
        print(f"   - {product.name}: ${product.price:.2f} (stock: {product.stock})")
    
    # Create or overwrite table
    print("\n5. Creating/updating LanceDB table 'menu_knowledge'...")
    
    # Drop existing table if exists
    try:
        db.drop_table("menu_knowledge")
        print("   Dropped existing table")
    except:
        pass
    
    table = db.create_table("menu_knowledge", data=documents)
    print(f"   Created table with {len(documents)} rows")
    
    # Verify with a test query
    print("\n6. Verifying with test queries...")
    test_queries = [
        "What's in the Zinger Burger?",
        "Any vegetarian options?",
        "How much is the double burger?",
        "Does the Coke have sugar?",
        "What sides do you have?",
        "Is the double burger in stock?",
    ]
    
    for query in test_queries:
        query_vector = embedder.encode(query).tolist()
        results = table.search(query_vector).limit(3).to_pandas()
        print(f"\n   Query: '{query}'")
        for _, row in results.iterrows():
            print(f"     → {row['name']} (score: {row['_distance']:.3f})")
    
    print("\n" + "=" * 60)
    print("✓ Menu Knowledge Seeding Complete!")
    print(f"Database location: {Path('.lancedb').absolute()}")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = asyncio.run(seed_menu_knowledge())
    sys.exit(0 if success else 1)