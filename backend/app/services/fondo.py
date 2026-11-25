"""Servicio de recorte automático de fondo para prendas."""

import colorsys
from collections import Counter
from io import BytesIO
from PIL import Image, ImageOps


def normalizar_orientacion_exif(imagen_bytes: bytes) -> bytes:
    """Aplica la rotación EXIF del celular para evitar fotos apaisadas."""
    img = Image.open(BytesIO(imagen_bytes))
    img = ImageOps.exif_transpose(img)
    buffer = BytesIO()
    formato = "PNG" if img.mode in ("RGBA", "LA", "P") else "JPEG"
    if formato == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buffer, format=formato)
    return buffer.getvalue()


def recortar_fondo_prenda(imagen_bytes: bytes) -> tuple[bytes, bool]:
    """
    Elimina el fondo de la fotografía de la prenda usando rembg (FOSS).
    Si rembg no está instalado aún, devuelve la imagen normalizada en PNG RGBA.
    Retorna (bytes_png, recorte_aplicado).
    """
    imagen_bytes = normalizar_orientacion_exif(imagen_bytes)
    try:
        from rembg import remove  # type: ignore

        salida = remove(imagen_bytes)
        return salida, True
    except ImportError:
        img = Image.open(BytesIO(imagen_bytes)).convert("RGBA")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue(), False


def _clasificar_rgb(r: int, g: int, b: int) -> str:
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    grados = h * 360.0
    if v < 0.20:
        return "negro"
    if s < 0.18:
        return "blanco" if v > 0.78 else "gris"
    if 25.0 <= grados <= 55.0 and (s < 0.50 or v > 0.65):
        return "beige"
    if grados >= 340.0 or grados < 25.0:
        return "rojo"
    if 75.0 <= grados <= 165.0:
        return "verde"
    if 185.0 <= grados <= 265.0:
        return "azul"
    return "otro"


def detectar_color_prenda(imagen_png_bytes: bytes) -> str:
    """Detecta el color dominante de una prenda ignorando píxeles transparentes."""
    img = Image.open(BytesIO(imagen_png_bytes)).convert("RGBA")
    img.thumbnail((64, 64))
    conteo: Counter[str] = Counter()
    for r, g, b, a in img.getdata():
        if a > 128:
            conteo[_clasificar_rgb(r, g, b)] += 1
    if not conteo:
        return "otro"
    return conteo.most_common(1)[0][0]
