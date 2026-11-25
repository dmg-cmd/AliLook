"""Adaptador simulado para validar el flujo completo sin consumir VRAM."""

from io import BytesIO
from PIL import Image, ImageDraw
from app.adapters.base import MotorTryOn
from app.models.schemas import CategoriaPrenda, ElasticidadTejido


class MotorSimulado(MotorTryOn):
    """Compone una vista previa rápida superponiendo la prenda sobre la zona objetivo."""

    nombre_proveedor = "simulado"

    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        persona = Image.open(BytesIO(persona_bytes)).convert("RGBA")
        prenda = Image.open(BytesIO(prenda_bytes)).convert("RGBA")

        ancho_p, alto_p = persona.size
        factor_ancho = int(ancho_p * 0.45)
        proporcion = factor_ancho / max(prenda.width, 1)
        nuevo_alto = max(1, int(prenda.height * proporcion))
        prenda_redim = prenda.resize((factor_ancho, nuevo_alto), Image.Resampling.LANCZOS)

        pos_x = (ancho_p - factor_ancho) // 2
        if categoria == CategoriaPrenda.SUPERIOR:
            pos_y = int(alto_p * 0.22)
        elif categoria == CategoriaPrenda.INFERIOR:
            pos_y = int(alto_p * 0.48)
        else:
            pos_y = int(alto_p * 0.22)

        composicion = persona.copy()
        composicion.alpha_composite(prenda_redim, dest=(pos_x, pos_y))

        dibujo = ImageDraw.Draw(composicion)
        dibujo.rectangle([(10, 10), (310, 42)], fill=(15, 23, 42, 200))
        dibujo.text((20, 20), f"Vista previa MVP ({categoria.value})", fill=(255, 255, 255, 255))

        salida = BytesIO()
        composicion.convert("RGB").save(salida, format="PNG")
        return salida.getvalue()
