"""Pruebas unitarias para el Failover Multi-Proveedor y BYOK."""

import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.adapters import failover
from app.adapters.byok_gemini import MotorBYOKGemini
from app.adapters.factory import obtener_motor_vto
from app.adapters.failover import MotorFailover
from app.models.schemas import CategoriaPrenda, ElasticidadTejido


def _png_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_failover_conmuta_tras_429_y_timeout(monkeypatch) -> None:
    llamadas: list[str] = []

    async def fake_comunitarios() -> list[str]:
        return ["https://nodo-saturado.ejemplo/tryon", "https://nodo-caido.ejemplo/tryon"]

    async def fake_llamar(url, persona_bytes, prenda_bytes, categoria, elasticidad, timeout_s):
        llamadas.append(url)
        if "saturado" in url:
            req = httpx.Request("POST", url)
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError("429 Too Many Requests", request=req, response=resp)
        raise httpx.TimeoutException("Timeout de 18s alcanzado")

    monkeypatch.setattr(failover, "obtener_endpoints_comunitarios", fake_comunitarios)
    monkeypatch.setattr(failover, "_llamar_endpoint_comunitario", fake_llamar)

    motor = MotorFailover(cadena=["nube_comunitaria", "simulado"])
    res = await motor.generar_prueba(
        _png_bytes(),
        _png_bytes(),
        CategoriaPrenda.SUPERIOR,
        ElasticidadTejido.MEDIO,
    )
    assert len(llamadas) == 2
    assert motor.nombre_proveedor == "simulado"
    assert res[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.anyio
async def test_failover_usa_segundo_nodo_comunitario_si_primero_da_503(monkeypatch) -> None:
    png_ok = _png_bytes()

    async def fake_comunitarios() -> list[str]:
        return ["https://nodo1.ejemplo/tryon", "https://nodo2.ejemplo/tryon"]

    async def fake_llamar(url, persona_bytes, prenda_bytes, categoria, elasticidad, timeout_s):
        if "nodo1" in url:
            req = httpx.Request("POST", url)
            resp = httpx.Response(503, request=req)
            raise httpx.HTTPStatusError("503 Service Unavailable", request=req, response=resp)
        return png_ok

    monkeypatch.setattr(failover, "obtener_endpoints_comunitarios", fake_comunitarios)
    monkeypatch.setattr(failover, "_llamar_endpoint_comunitario", fake_llamar)

    motor = MotorFailover(cadena=["nube_comunitaria", "simulado"])
    res = await motor.generar_prueba(
        png_ok,
        png_ok,
        CategoriaPrenda.INFERIOR,
        ElasticidadTejido.RIGIDO,
    )
    assert res == png_ok
    assert motor.nombre_proveedor == "nube_comunitaria#2"


@pytest.mark.anyio
async def test_byok_gemini_sin_clave_falla_limpiamente() -> None:
    motor = MotorBYOKGemini(api_key="")
    with pytest.raises(RuntimeError, match="No hay clave BYOK"):
        await motor.generar_prueba(
            _png_bytes(),
            _png_bytes(),
            CategoriaPrenda.SUPERIOR,
            ElasticidadTejido.ELASTICO,
        )


def test_factory_acepta_failover_y_auto() -> None:
    assert isinstance(obtener_motor_vto("auto"), MotorFailover)
    assert isinstance(obtener_motor_vto("failover"), MotorFailover)
    assert isinstance(obtener_motor_vto("byok_gemini", byok_api_key="demo"), MotorBYOKGemini)
