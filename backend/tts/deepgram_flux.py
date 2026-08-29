import os
import requests


class DeepgramFluxTTS:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self.base_url = "https://openrouter.ai/api/v1"

    def speak(self, text: str, voice: str = "flux-alexis-en") -> bytes:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepgram/flux-tts",
            "input": text,
            "voice": voice,
            "response_format": "mp3"
        }
        response = requests.post(
            f"{self.base_url}/audio/speech",
            headers=headers,
            json=data
        )
        if response.status_code != 200:
            raise Exception(f"TTS error: {response.status_code} - {response.text}")
        return response.content
