import asyncio
from app.core.rag_engine import get_rag_engine

rag = get_rag_engine()

questions = [
    'How much is the double burger?',
    'Is the double burger in stock?',
    'What sides do you have?',
    'Any vegetarian options?',
    'Does the Coke have sugar?'
]

for q in questions:
    result = asyncio.run(rag.query(q))
    print(f'Q: {q}')
    print(f'A: {result["answer"]}')
    print(f'Confidence: {result["confidence"]}')
    print('---')