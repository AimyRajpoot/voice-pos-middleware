import numpy as np
from typing import Optional
import tempfile
import os


class ParakeetSTT:
    def __init__(self):
        try:
            from nano_parakeet import from_pretrained
            self.model = from_pretrained()
            self.use_nano_parakeet = True
        except ImportError:
            from transformers import pipeline
            self.model = pipeline(
                "automatic-speech-recognition",
                model="nvidia/parakeet-tdt-0.6b-v3",
                device="cpu"
            )
            self.use_nano_parakeet = False

    def transcribe(self, audio_data: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            if self.use_nano_parakeet:
                result = self.model.transcribe(temp_path)
                return result.text.strip() if hasattr(result, 'text') else str(result).strip()
            else:
                result = self.model(temp_path)
                return result["text"].strip()
        finally:
            os.unlink(temp_path)
