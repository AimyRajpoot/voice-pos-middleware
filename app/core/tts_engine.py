import os
import base64
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional
import edge_tts

class TTSEngine:
    """
    Edge TTS wrapper for high-quality text-to-speech.
    Uses Microsoft Edge's neural voices (free, no API key needed).
    Fully async-compatible for FastAPI.
    """
    
    # High-quality English voices
    VOICES = {
        "en_US-aria": "en-US-AriaNeural",      # Natural female (default)
        "en_US-guy": "en-US-GuyNeural",        # Natural male
        "en_US-jenny": "en-US-JennyNeural",    # Warm female
        "en_UK-libby": "en-GB-LibbyNeural",    # British female
        "en_UK-ryan": "en-GB-RyanNeural",      # British male
    }
    
    DEFAULT_VOICE_KEY = "en_US-aria"
    
    def __init__(self, voice_key: str = DEFAULT_VOICE_KEY):
        self.voice_key = voice_key
        self.voice = self.VOICES.get(voice_key, self.VOICES[self.DEFAULT_VOICE_KEY])
        self._initialized = True
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to MP3 audio bytes using Edge TTS.
        Returns raw MP3 data.
        """
        communicate = edge_tts.Communicate(text, self.voice)
        
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        return bytes(audio_data)
    
    async def synthesize_base64(self, text: str) -> str:
        """Synthesize and return base64 encoded audio."""
        audio_bytes = await self.synthesize(text)
        return base64.b64encode(audio_bytes).decode("utf-8")
    
    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream audio chunks for low-latency playback.
        Yields MP3 chunks.
        """
        communicate = edge_tts.Communicate(text, self.voice)
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
                await asyncio.sleep(0)  # Yield control
    
    def list_voices(self) -> dict:
        """Return available voice options."""
        return self.VOICES.copy()
    
    def set_voice(self, voice_key: str):
        """Change the active voice."""
        if voice_key in self.VOICES:
            self.voice_key = voice_key
            self.voice = self.VOICES[voice_key]
        else:
            raise ValueError(f"Unknown voice: {voice_key}. Available: {list(self.VOICES.keys())}")


# Global singleton instance
_tts_engine: Optional[TTSEngine] = None

def get_tts_engine(voice_key: str = TTSEngine.DEFAULT_VOICE_KEY) -> TTSEngine:
    global _tts_engine
    if _tts_engine is None or _tts_engine.voice_key != voice_key:
        _tts_engine = TTSEngine(voice_key)
    return _tts_engine