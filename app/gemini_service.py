import requests

from app.config import settings


class GeminiError(Exception):
    """Cubre cualquier fallo al llamar a Gemini: timeout, red, HTTP,
    respuesta con forma inesperada, o API key no configurada."""


class GeminiService:
    def __init__(self):
        self.base_url = settings.GEMINI_BASE_URL
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS

    def generar_texto(self, prompt: str) -> str:
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY no está configurada")

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise GeminiError(f"Fallo al llamar a Gemini: {e}") from e

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            raise GeminiError(f"Respuesta inesperada de Gemini: {data}") from e


gemini_service = GeminiService()
