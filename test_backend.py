import asyncio
from app.core.langgraph_pipeline import LangGraphVoicePOSPipeline
from app.adapters.mock_pos import MockPOSAdapter

async def test():
    p = LangGraphVoicePOSPipeline(MockPOSAdapter())
    r = await p.process_voice_text('I want a zinger burger and fries')
    print('Test 1:', r.get('status'), r.get('items'))
    r2 = await p.process_voice_text('Can I get a pizza?')
    print('Test 2:', r2.get('status'))
    r3 = await p.process_voice_text('How much is the zinger burger?')
    print('Test 3:', r3.get('status'))

asyncio.run(test())