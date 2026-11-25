"""Adaptador opcional BYOK (Bring Your Own Key) para APIs generativas con nivel gratuito."""

import base64
import httpx

from app.adapters.base import MotorTryOn
from app.core.config import VTO_BYOK_GEMINI_KEY, VTO_FAILOVER_TIMEOUT_S
from app.models.schemas import CategoriaPrenda, ElasticidadTejido


class MotorBYOKGemini(MotorTryOn):
    """
    Usa la API multimodal gratuita de Google AI Studio (Gemini) únicamente si el
    usuario provee su propia clave (BYOK) o la configura en el entorno.
    """

    nombre_proveedor = "byok_gemini"

    def __init__(self, api_key: str | None = None, timeout_s: float = VTO_FAILOVER_TIMEOUT_S):
        self.api_key = (api_key or VTO_BYOK_GEMINI_KEY).strip()
        self.timeout_s = timeout_s

    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        if not self.api_key:
            raise RuntimeError("No hay clave BYOK configurada para Gemini.")

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash-exp-image-generation:generateContent?key={self.api_key}"
        )
        prompt = (
            "Virtual try-on: viste a la persona de la primera imagen con la prenda "
            f"({categoria.value}, tejido {elasticidad.value}) de la segunda imagen. "
            "Mantén intactos el rostro, postura, contextura física y fondo."
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64.b64encode(persona_bytes).decode("ascii"),
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(prenda_bytes).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()

        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])

        raise RuntimeError("La respuesta BYOK no devolvió ninguna imagen.")
