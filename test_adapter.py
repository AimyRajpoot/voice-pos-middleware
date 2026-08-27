import asyncio
from app.adapters.mock_pos import MockPOSAdapter

async def main():
    adapter = MockPOSAdapter()
    
    print("Testing fetch_products()...")
    products = await adapter.fetch_products()
    print("Products fetched successfully:", products)

if __name__ == "__main__":
    asyncio.run(main())