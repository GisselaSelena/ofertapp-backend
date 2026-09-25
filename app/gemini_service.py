import time

import requests

from app.config import settings


class GeminiError(Exception):
    """Cubre cualquier fallo al llamar a Gemini: timeout, red, HTTP,
    respuesta con forma inesperada, o API key no configurada."""


# 429 (cuota) y 5xx son errores típicamente transitorios del lado de
# Gemini/Google — vale la pena reintentar. 4xx de autenticación/formato
# (401, 403, 404, 400) no se reintentan: fallarían igual todas las veces.
CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}
MAX_INTENTOS = 3  # intento inicial + 2 reintentos
ESPERA_ENTRE_INTENTOS_SEGUNDOS = 1.5


class GeminiService:
    def __init__(self):
        self.base_url = settings.GEMINI_BASE_URL
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS

    def generar_texto(self, prompt: str) -> str:
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY no está configurada")

        # OJO: `url` nunca debe llevar la API key embebida (va aparte, en
        # `params`) — así el logueo de errores no filtra la key.
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"

        for intento in range(1, MAX_INTENTOS + 1):
            try:
                response = requests.post(
                    url,
                    params={"key": self.api_key},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=self.timeout,
                )
            except requests.RequestException as e:
                if intento < MAX_INTENTOS:
                    print(
                        f"🔁 Gemini intento {intento}/{MAX_INTENTOS} falló por "
                        f"error de red ({e}); reintentando en "
                        f"{ESPERA_ENTRE_INTENTOS_SEGUNDOS}s..."
                    )
                    time.sleep(ESPERA_ENTRE_INTENTOS_SEGUNDOS)
                    continue
                raise GeminiError(f"Fallo de red al llamar a Gemini: {e}") from e

            if response.status_code in CODIGOS_REINTENTABLES and intento < MAX_INTENTOS:
                print(
                    f"🔁 Gemini intento {intento}/{MAX_INTENTOS} devolvió "
                    f"HTTP {response.status_code} ({response.reason}) — probable "
                    f"sobrecarga transitoria; reintentando en "
                    f"{ESPERA_ENTRE_INTENTOS_SEGUNDOS}s. Cuerpo: {response.text[:300]}"
                )
                time.sleep(ESPERA_ENTRE_INTENTOS_SEGUNDOS)
                continue

            if not response.ok:
                # Mensaje explícito con código + cuerpo real de Gemini, sin
                # la API key (no está en `url`, y no reconstruimos la URL
                # final de `requests`, que sí la llevaría en el query string).
                raise GeminiError(
                    f"Gemini respondió HTTP {response.status_code} "
                    f"({response.reason}) en el intento {intento}/{MAX_INTENTOS} "
                    f"para modelo '{self.model}'. Cuerpo de la respuesta: "
                    f"{response.text[:500]}"
                )

            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as e:
                raise GeminiError(f"Respuesta inesperada de Gemini: {data}") from e

        # Inalcanzable: el loop siempre retorna o lanza antes de terminar.
        raise GeminiError("Fallo desconocido al llamar a Gemini")


gemini_service = GeminiService()
