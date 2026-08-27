import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import lancedb
from sentence_transformers import SentenceTransformer
from app.adapters.mock_pos import MockPOSAdapter
from app.schemas.pos import ProductSchema

class MenuRAGEngine:
    """
    RAG Engine for Menu Q&A using LanceDB vector database.
    Provides semantic search over menu items with LLM synthesis.
    """
    
    def __init__(self, db_path: str = ".lancedb", embedder_model: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.embedder = SentenceTransformer(embedder_model)
        self.db = lancedb.connect(db_path)
        self.table = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the database connection and table."""
        if self._initialized:
            return
        
        try:
            self.table = self.db.open_table("menu_knowledge")
            self._initialized = True
            print(f"RAG Engine initialized with {len(self.table)} menu items")
        except Exception as e:
            print(f"RAG Engine initialization failed: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if the engine is ready to serve queries."""
        return self._initialized and self.table is not None
    
    def seed_from_pos(self, products: List[ProductSchema]) -> int:
        """Seed the vector database from POS products."""
        documents = []
        
        for product in products:
            text_parts = [
                f"Item: {product.name}",
                f"Category: {product.category or 'Uncategorized'}",
                f"Price: ${product.price:.2f}",
                f"Stock: {product.stock} units",
            ]
            
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
                "vector": self.embedder.encode(full_text).tolist()
            })
        
        try:
            self.db.drop_table("menu_knowledge")
        except:
            pass
        
        self.table = self.db.create_table("menu_knowledge", data=documents)
        self._initialized = True
        print(f"Seeded {len(documents)} menu items into vector DB")
        return len(documents)
    
    async def query(self, question: str, k: int = 3, similarity_threshold: float = 1.5) -> Dict[str, Any]:
        """
        Query the menu knowledge base.
        Returns answer with citations.
        """
        if not self._initialized:
            self.initialize()
        
        if not self.table:
            return {
                "answer": "Menu knowledge base is not initialized. Please run seeding script.",
                "citations": [],
                "confidence": 0.0
            }
        
        query_vector = self.embedder.encode(question).tolist()
        results = self.table.search(query_vector).limit(k).to_pandas()
        
        if results.empty:
            return {
                "answer": "I don't have information about that. Let me check with the kitchen!",
                "citations": [],
                "confidence": 0.0
            }
        
        relevant_results = results[results['_distance'] <= similarity_threshold]
        
        if relevant_results.empty:
            return {
                "answer": "I'm not sure about that. Let me check with the kitchen!",
                "citations": [],
                "confidence": 0.0
            }
        
        context_parts = []
        citations = []
        
        for _, row in relevant_results.iterrows():
            context_parts.append(f"Item: {row['name']}\n{row['text']}")
            citations.append({
                "name": row['name'],
                "category": row['category'],
                "price": row['price'],
                "stock": row['stock'],
                "relevance_score": round(1.0 - row['_distance'], 3)
            })
        
        top_result = relevant_results.iloc[0]
        answer = self._generate_answer(question, relevant_results)
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": round(1.0 - top_result['_distance'], 3)
        }
    
    def _generate_answer(self, question: str, results) -> str:
        """Generate a natural language answer based on query and results."""
        question_lower = question.lower()
        top = results.iloc[0]
        
        if any(w in question_lower for w in ["price", "cost", "how much", "expensive", "cheap"]):
            return f"The {top['name']} costs ${top['price']:.2f}."
        
        if any(w in question_lower for w in ["stock", "available", "in stock", "out of stock"]):
            if top['stock'] == 0:
                return f"The {top['name']} is currently out of stock."
            elif top['stock'] < 5:
                return f"The {top['name']} has low stock - only {top['stock']} left."
            else:
                return f"The {top['name']} is in stock ({top['stock']} available)."
        
        if any(w in question_lower for w in ["what", "ingredient", "contain", "made of", "have in", "what's in"]):
            desc_start = top['text'].find("Description:")
            if desc_start != -1:
                desc = top['text'][desc_start + 12:].split('\n')[0].strip()
                return f"The {top['name']} contains: {desc}"
            return f"The {top['name']} is a {top['category']} item priced at ${top['price']:.2f}."
        
        if any(w in question_lower for w in ["vegetarian", "vegan", "gluten", "dietary", "allergen"]):
            if "vegetarian" in question_lower or "vegan" in question_lower:
                veg_items = [r['name'] for _, r in results.iterrows() if 'vegetarian' in r['text'].lower() or 'vegan' in r['text'].lower()]
                if veg_items:
                    return f"Vegetarian options: {', '.join(veg_items)}."
                return "We don't have vegetarian options currently."
            if "gluten" in question_lower:
                gf_items = [r['name'] for _, r in results.iterrows() if 'gluten-free' in r['text'].lower()]
                if gf_items:
                    return f"Gluten-free options: {', '.join(gf_items)}."
                return "Most items contain gluten. Fries are gluten-free."
        
        if any(w in question_lower for w in ["side", "sides", "category", "menu"]):
            categories = {}
            for _, r in results.iterrows():
                cat = r['category'] or 'Other'
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(r['name'])
            
            cat_strs = [f"{cat}: {', '.join(items)}" for cat, items in categories.items()]
            return "Our menu includes: " + "; ".join(cat_strs) + "."
        
        return f"{top['name']} - ${top['price']:.2f} ({top['category']}). {top['text'].split('Description:')[-1].split('\n')[0].strip() if 'Description:' in top['text'] else ''}"


_rag_engine: Optional[MenuRAGEngine] = None

def get_rag_engine(db_path: str = ".lancedb") -> MenuRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = MenuRAGEngine(db_path)
    return _rag_engine