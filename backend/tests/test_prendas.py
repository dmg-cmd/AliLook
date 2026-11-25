"""Pruebas del endpoint de recorte de prendas para el Armario Digital."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def _crear_png_prueba() -> bytes:
    img = Image.new("RGB", (64, 64), color=(30, 120, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_recortar_prenda_devuelve_base64() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/v1/prendas/recortar",
        files={"prenda": ("camisa.png", _crear_png_prueba(), "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "imagen_recortada_base64" in data
    assert len(data["imagen_recortada_base64"]) > 20
    assert isinstance(data["recorte_aplicado"], bool)
    assert data["color_detectado"] == "azul"
    assert "azul" in data["nombre_sugerido"]


def test_recortar_prenda_vacia_falla() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/v1/prendas/recortar",
        files={"prenda": ("vacia.png", b"", "image/png")},
    )
    assert resp.status_code == 400
