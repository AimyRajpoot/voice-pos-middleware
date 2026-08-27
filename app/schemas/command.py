from pydantic import BaseModel
from typing import Optional, List

class ExtractedEntity(BaseModel):
    raw_text: str
    matched_product_id: Optional[str] = None
    quantity: int = 1
    confidence_score: float = 0.0

class VoiceCommandIntent(BaseModel):
    intent_type: str  # e.g., "ADD_TO_ORDER", "CHECK_STOCK", "CANCEL_ORDER"
    entities: List[ExtractedEntity] = []
    original_transcript: str