"""Interfaz base para motores de Virtual Try-On intercambiables."""

from abc import ABC, abstractmethod
from app.models.schemas import CategoriaPrenda, ElasticidadTejido


class MotorTryOn(ABC):
    """Contrato único que deben implementar los proveedores locales o en la nube."""

    nombre_proveedor: str = "base"

    @abstractmethod
    async def generar_prueba(
        self,
        persona_bytes: bytes,
        prenda_bytes: bytes,
        categoria: CategoriaPrenda,
        elasticidad: ElasticidadTejido,
    ) -> bytes:
        """Genera y devuelve la imagen resultado en formato PNG."""
        raise NotImplementedError
