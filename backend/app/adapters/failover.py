"""Adaptador de conmutación automática (Failover Multi-Proveedor) para VTO."""

import base64
import logging
import time
from typing import Iterable

import httpx

from app.adapters.base import MotorTryOn
from app.adapters.byok_gemini import MotorBYOKGemini
from app.adapters.fashn_local import MotorFashnLocal
from app.adapters.nube_http import MotorNubeHTTP
from app.adapters.simulado import MotorSimulado
from app.core.config import (
    VTO_CLOUD_URL,
    VTO_COMMUNITY_ENDPOINTS,
    VTO_FAILOVER_CADENA,
    VTO_FAILOVER_TIMEOUT_S,
    VTO_REMOTE_ENDPOINTS_URL,
    WEIGHTS_FASHN,
)
from app.models.schemas import CategoriaPrenda, ElasticidadTejido

logger = logging.getLogger("alilook.failover")

CODIGOS_REINTENTO = {429, 502, 503, 504}
_CACHE_REMOTO: dict[str, object] = {"ts": 0.0, "endpoints": []}
_TTL_CACHE_REMOTO_S = 300.0


async def obtener_endpoints_comunitarios() -> list[str]:
    """Obtiene la lista de nodos comunitarios desde entorno y/o JSON remoto."""
    urls: list[str] = list(VTO_COMMUNITY_ENDPOINTS)
    if VTO_CLOUD_URL and VTO_CLOUD_URL not in urls:
        urls.append(VTO_CLOUD_URL)

    if VTO_REMOTE_ENDPOINTS_URL:
        ahora = time.monotonic()
        if ahora - float(_CACHE_REMOTO["ts"]) > _TTL_CACHE_REMOTO_S:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(VTO_REMOTE_ENDPOINTS_URL)
                    resp.raise_for_status()
                    data = resp.json()
                    remotos = []
                    for item in data.get("endpoints", []):
                        if isinstance(item, str) and item.strip():
                            remotos.append(item.strip())
                        elif isinstance(item, dict) and item.get("url"):
                            remotos.append(str(item["url"]).strip())
                    _CACHE_REMOTO["endpoints"] = remotos
                    _CACHE_REMOTO["ts"] = ahora
            except Exception as ex:
                logger.warning("No se pudo actualizar la lista remota de endpoints: %s", ex)

        for u in _CACHE_REMOTO["endpoints"]:
            if u not in urls:
                urls.append(u)

    return urls


async def _llamar_endpoint_comunitario(
    url: str,
    persona_bytes: bytes,
    prenda_bytes: bytes,
    categoria: CategoriaPrenda,
    elasticidad: ElasticidadTejido,
    timeout_s: float,
) -> bytes:
    """Envía la prueba a un nodo comunitario con timeout corto."""
    files = {
        "persona": ("persona.png", persona_bytes, "image/png"),
        "prenda": ("prenda.png", prenda_bytes, "image/png"),
    }
    data = {"categoria": categoria.value, "elasticidad": elasticidad.value}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, files=files, data=data)
        if resp.status_code in CODIGOS_REINTENTO:
            raise httpx.HTTPStatusError(
                f"Nodo comunitario saturado ({resp.status_code})",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        contenido = resp.json()
        return base64.b64decode(contenido["imagen_resultado_base64"])


class MotorFailover(MotorTryOn):
    """
    Ejecuta una cadena de proveedores VTO con timeouts cortos y conmutación
    automática ante errores de cuota (429), disponibilidad (503/504) o red.
    """

    nombre_proveedor = "failover"

    def __init__(
        self,
        cadena: Iterable[str] | None = None,
        byok_api_key: str | None = None,
        timeout_s: float = VTO_FAILOVER_TIMEOUT_S,
    ):
        self.cadena = list(cadena) if cadena is not None else list(VTO_FAILOVER_CADENA)
        self.byok_api_key = byok_api_key
        self.timeout_s = timeout_s

    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        errores: list[str] = []

        for paso in self.cadena:
            try:
                if paso == "fashn_local":
                    if not WEIGHTS_FASHN.exists():
                        continue
                    motor = MotorFashnLocal()
                    res = await motor.generar_prueba(persona_bytes, prenda_bytes, categoria, elasticidad)
                    self.nombre_proveedor = motor.nombre_proveedor
                    return res

                if paso == "nube_comunitaria":
                    endpoints = await obtener_endpoints_comunitarios()
                    for idx, url in enumerate(endpoints, start=1):
                        try:
                            res = await _llamar_endpoint_comunitario(
                                url, persona_bytes, prenda_bytes, categoria, elasticidad, self.timeout_s
                            )
                            self.nombre_proveedor = f"nube_comunitaria#{idx}"
                            return res
                        except Exception as ex:
                            errores.append(f"nube_comunitaria#{idx}: {ex}")
                    continue

                if paso == "nube_http":
                    if not VTO_CLOUD_URL:
                        continue
                    motor = MotorNubeHTTP()
                    res = await motor.generar_prueba(persona_bytes, prenda_bytes, categoria, elasticidad)
                    self.nombre_proveedor = motor.nombre_proveedor
                    return res

                if paso == "byok_gemini":
                    motor = MotorBYOKGemini(api_key=self.byok_api_key, timeout_s=self.timeout_s)
                    if not motor.api_key:
                        continue
                    res = await motor.generar_prueba(persona_bytes, prenda_bytes, categoria, elasticidad)
                    self.nombre_proveedor = motor.nombre_proveedor
                    return res

                if paso == "simulado":
                    motor = MotorSimulado()
                    res = await motor.generar_prueba(persona_bytes, prenda_bytes, categoria, elasticidad)
                    self.nombre_proveedor = motor.nombre_proveedor
                    return res

            except Exception as ex:
                logger.warning("Fallo en proveedor '%s', conmutando al siguiente: %s", paso, ex)
                errores.append(f"{paso}: {ex}")

        raise RuntimeError(
            "Todos los proveedores de la cadena failover fallaron: " + "; ".join(errores)
        )
