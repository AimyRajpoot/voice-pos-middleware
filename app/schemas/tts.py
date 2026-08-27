from pydantic import BaseModel
from typing import Optional

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en_US-aria"  # Voice key: en_US-aria, en_US-guy, en_US-jenny, en_UK-libby, en_UK-ryan
    stream: Optional[bool] = False

class TTSResponse(BaseModel):
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    duration_ms: int
    voice: str