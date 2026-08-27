from pydantic import BaseModel
from typing import Optional, List

class QARequest(BaseModel):
    question: str
    k: Optional[int] = 3
    similarity_threshold: Optional[float] = 1.5

class Citation(BaseModel):
    name: str
    category: str
    price: float
    stock: int
    relevance_score: float

class QAResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    confidence: float