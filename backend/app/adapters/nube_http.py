"""Adaptador HTTP para delegar la inferencia a un servidor GPU en la nube."""

import base64
import httpx
from app.adapters.base import MotorTryOn
from app.core.config import VTO_CLOUD_TOKEN, VTO_CLOUD_URL
from app.models.schemas import CategoriaPrenda, ElasticidadTejido


class MotorNubeHTTP(MotorTryOn):
    """Envía la petición al servidor remoto configurado en VTO_CLOUD_URL."""

    nombre_proveedor = "nube_http"

    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        if not VTO_CLOUD_URL:
            raise RuntimeError("VTO_CLOUD_URL no está configurado en el entorno.")

        headers = {}
        if VTO_CLOUD_TOKEN:
            headers["Authorization"] = f"Bearer {VTO_CLOUD_TOKEN}"

        files = {
            "persona": ("persona.png", persona_bytes, "image/png"),
            "prenda": ("prenda.png", prenda_bytes, "image/png"),
        }
        data = {
            "categoria": categoria.value,
            "elasticidad": elasticidad.value,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(VTO_CLOUD_URL, files=files, data=data, headers=headers)
            resp.raise_for_status()
            contenido = resp.json()
            return base64.b64decode(contenido["imagen_resultado_base64"])
