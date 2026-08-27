import asyncio
from app.adapters.mock_pos import MockPOSAdapter
from app.schemas.pos import ProductSchema
from app.nlp.product_matcher import ProductMatcher
from app.nlp.intent_extractor import IntentExtractor

async def main():
    # 1. Fetch live catalog from POS
    adapter = MockPOSAdapter()
    raw_products = await adapter.fetch_products()
    catalog = [ProductSchema(**p) for p in raw_products]

    # 2. Initialize Matcher & Extractor
    matcher = ProductMatcher(catalog)
    extractor = IntentExtractor(matcher)

    # 3. Test raw spoken phrases
    sample_voice_input = "add 2 zinger burgers and 1 coca cola zero"
    print(f"User Spoke: '{sample_voice_input}'\n")

    result = extractor.parse_command(sample_voice_input)
    
    print("--- Extracted Intent Payload ---")
    print(f"Intent Type: {result.intent_type}")
    for entity in result.entities:
        print(f"  • Raw Text: '{entity.raw_text}' | Qty: {entity.quantity} | Matched Product ID: {entity.matched_product_id} | Confidence: {entity.confidence_score}%")

if __name__ == "__main__":
    asyncio.run(main())