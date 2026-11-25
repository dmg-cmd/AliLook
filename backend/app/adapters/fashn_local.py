"""Adaptador local para FASHN VTON v1.5 (Apache 2.0) en GPU NVIDIA (RTX 3080 8 GB)."""

import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.adapters.base import MotorTryOn
from app.models.schemas import CategoriaPrenda, ElasticidadTejido

WEIGHTS_DIR = Path(__file__).resolve().parents[3] / "models" / "fashn-vton-1.5" / "weights"

MAPA_CATEGORIAS = {
    CategoriaPrenda.SUPERIOR: "tops",
    CategoriaPrenda.INFERIOR: "bottoms",
    CategoriaPrenda.CUERPO_ENTERO: "one-pieces",
}


class MotorFashnLocal(MotorTryOn):
    """Ejecuta FASHN VTON v1.5 localmente en GPU CUDA."""

    nombre_proveedor = "fashn_local"
    _pipeline_compartido = None

    def __init__(self, garment_photo_type: str = "model"):
        self.garment_photo_type = garment_photo_type if garment_photo_type in ("model", "flat-lay") else "model"

    def _obtener_pipeline(self):
        if MotorFashnLocal._pipeline_compartido is not None:
            return MotorFashnLocal._pipeline_compartido

        try:
            import torch  # type: ignore
            from fashn_vton import TryOnPipeline  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PyTorch o fashn-vton no están instalados en el entorno."
            ) from exc

        if not torch.cuda.is_available():
            raise RuntimeError("No se detectó GPU CUDA disponible para fashn_local.")

        if not WEIGHTS_DIR.exists():
            raise RuntimeError(
                f"No se encontraron los pesos del modelo en {WEIGHTS_DIR}."
            )

        MotorFashnLocal._pipeline_compartido = TryOnPipeline(weights_dir=str(WEIGHTS_DIR))
        return MotorFashnLocal._pipeline_compartido

    def _a_rgb_sobre_blanco(self, imagen_bytes: bytes) -> Image.Image:
        """Convierte a RGB componiendo cualquier canal alfa sobre fondo blanco limpio."""
        img = Image.open(BytesIO(imagen_bytes))
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            fondo = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
            return Image.alpha_composite(fondo, img_rgba).convert("RGB")
        return img.convert("RGB")

    def _inferir_sincrono(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
    ) -> bytes:
        pipeline = self._obtener_pipeline()
        persona_img = self._a_rgb_sobre_blanco(persona_bytes)
        prenda_img = self._a_rgb_sobre_blanco(prenda_bytes)

        resultado = pipeline(
            person_image=persona_img,
            garment_image=prenda_img,
            category=MAPA_CATEGORIAS[categoria],
            garment_photo_type=self.garment_photo_type,
            num_timesteps=25,
            segmentation_free=True,
        )

        buffer = BytesIO()
        resultado.images[0].save(buffer, format="PNG")
        return buffer.getvalue()

    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        return await asyncio.to_thread(
            self._inferir_sincrono,
            persona_bytes,
            prenda_bytes,
            categoria,
        )
