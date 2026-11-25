"""Fábrica de adaptadores de Virtual Try-On según configuración."""

from app.adapters.base import MotorTryOn
from app.adapters.byok_gemini import MotorBYOKGemini
from app.adapters.failover import MotorFailover
from app.adapters.fashn_local import MotorFashnLocal
from app.adapters.nube_http import MotorNubeHTTP
from app.adapters.simulado import MotorSimulado
from app.core.config import VTO_PROVIDER


def obtener_motor_vto(
    proveedor: str | None = None,
    byok_api_key: str | None = None,
) -> MotorTryOn:
    """Devuelve la instancia del motor VTO solicitado."""
    clave = (proveedor or VTO_PROVIDER).strip().lower()
    if clave in ("auto", "failover"):
        return MotorFailover(byok_api_key=byok_api_key)
    if clave == "simulado":
        return MotorSimulado()
    if clave == "fashn_local":
        return MotorFashnLocal()
    if clave == "nube_http":
        return MotorNubeHTTP()
    if clave == "byok_gemini":
        return MotorBYOKGemini(api_key=byok_api_key)
    raise ValueError(
        f"Proveedor VTO desconocido: '{clave}'. Usa 'auto', 'failover', 'simulado', 'fashn_local', 'nube_http' o 'byok_gemini'."
    )
