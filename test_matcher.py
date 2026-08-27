import asyncio
from app.adapters.mock_pos import MockPOSAdapter
from app.schemas.pos import ProductSchema
from app.nlp.product_matcher import ProductMatcher

async def main():
    # 1. Fetch live products from POS
    adapter = MockPOSAdapter()
    raw_products = await adapter.fetch_products()
    
    # 2. Parse into ProductSchema objects
    catalog = [ProductSchema(**p) for p in raw_products]
    
    # 3. Initialize Matcher
    matcher = ProductMatcher(catalog)
    
    # 4. Test fuzzy queries
    test_queries = ["zinger", "coca cola zero", "chickn burger", "fries"]
    
    print("--- Product Matching Results ---")
    for query in test_queries:
        product, score = matcher.match_product(query)
        if product:
            print(f"Query: '{query}' -> Matched: '{product.name}' (ID: {product.id}) | Confidence: {score}%")
        else:
            print(f"Query: '{query}' -> No match found (Score: {score}%)")

if __name__ == "__main__":
    asyncio.run(main())