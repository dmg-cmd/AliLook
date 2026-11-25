"""Punto de entrada de la API REST FastAPI - Proyecto Ali."""

import base64
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.factory import obtener_motor_vto
from app.core.config import (
    APP_NAME,
    APP_VERSION,
    VTO_AUTO_BORRAR_TEMPORALES,
    VTO_FAILOVER_CADENA,
    VTO_PROVIDER,
)
from app.models.schemas import (
    CategoriaPrenda,
    Complexion,
    ElasticidadTejido,
    MedidasCorporales,
    RecomendacionTalle,
    ResultadoTryOn,
)
from app.services.descubrimiento import ServidorDescubrimientoUDP
from app.services.fondo import (
    detectar_color_prenda,
    normalizar_orientacion_exif,
    recortar_fondo_prenda,
)
from app.services.talles import recomendar_talle

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicia y detiene el servicio de descubrimiento automático UDP en la red local."""
    descubrimiento = ServidorDescubrimientoUDP(puerto_http=8000)
    try:
        descubrimiento.iniciar()
    except OSError:
        pass
    try:
        yield
    finally:
        descubrimiento.detener()


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def inicio() -> FileResponse:
    """Sirve la interfaz web móvil ligera para pruebas desde Android sin caché."""
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/v1/salud")
async def salud() -> dict:
    """Devuelve el estado del servidor y el proveedor de IA activo."""
    return {
        "estado": "ok",
        "version": APP_VERSION,
        "proveedor_ia": VTO_PROVIDER,
        "failover_cadena": VTO_FAILOVER_CADENA,
    }


@app.post("/api/v1/talle", response_model=RecomendacionTalle)
async def calcular_talle(
    medidas: MedidasCorporales,
    categoria: CategoriaPrenda = CategoriaPrenda.SUPERIOR,
    elasticidad: ElasticidadTejido = ElasticidadTejido.MEDIO,
) -> RecomendacionTalle:
    """Calcula el talle recomendado sin procesar imágenes."""
    return recomendar_talle(medidas, categoria=categoria, elasticidad=elasticidad)


@app.post("/api/v1/prendas/recortar")
async def recortar_prenda(
    prenda: UploadFile = File(..., description="Fotografía de la prenda a recortar"),
    categoria: str = Form("superior"),
) -> dict:
    """Recorta el fondo de una prenda y detecta su color y nombre sugerido."""
    prenda_bytes = await prenda.read()
    if not prenda_bytes:
        raise HTTPException(status_code=400, detail="La imagen de la prenda no puede estar vacía.")

    prenda_png, recorte_aplicado = recortar_fondo_prenda(prenda_bytes)
    color = detectar_color_prenda(prenda_png)
    cat_legible = categoria.strip().replace("_", " ") or "superior"
    return {
        "imagen_recortada_base64": base64.b64encode(prenda_png).decode("ascii"),
        "recorte_aplicado": recorte_aplicado,
        "color_detectado": color,
        "nombre_sugerido": f"Prenda {cat_legible} {color}",
    }


@app.post("/api/v1/try-on", response_model=ResultadoTryOn)
async def probar_prenda(
    persona: UploadFile = File(..., description="Fotografía frontal del usuario"),
    prenda: UploadFile = File(..., description="Fotografía de la prenda"),
    consentimiento_privacidad: bool = Form(...),
    altura_cm: float = Form(...),
    peso_kg: float = Form(...),
    complexion: Complexion = Form(Complexion.MEDIA),
    categoria: CategoriaPrenda = Form(CategoriaPrenda.SUPERIOR),
    elasticidad: ElasticidadTejido = Form(ElasticidadTejido.MEDIO),
    pecho_cm: Optional[float] = Form(None),
    cintura_cm: Optional[float] = Form(None),
    cadera_cm: Optional[float] = Form(None),
    hombros_cm: Optional[float] = Form(None),
    proveedor: Optional[str] = Form(None),
    byok_api_key: Optional[str] = Form(None),
    tipo_foto_prenda: str = Form("model"),
) -> ResultadoTryOn:
    """Ejecuta el flujo completo: validación de privacidad, talle, recorte y síntesis VTO."""
    if not consentimiento_privacidad:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar el consentimiento temporal de procesamiento de imagen.",
        )

    persona_bytes = await persona.read()
    prenda_bytes = await prenda.read()
    if not persona_bytes or not prenda_bytes:
        raise HTTPException(status_code=400, detail="Las imágenes no pueden estar vacías.")

    medidas = MedidasCorporales(
        altura_cm=altura_cm,
        peso_kg=peso_kg,
        complexion=complexion,
        pecho_cm=pecho_cm,
        cintura_cm=cintura_cm,
        cadera_cm=cadera_cm,
        hombros_cm=hombros_cm,
    )
    rec_talle = recomendar_talle(medidas, categoria=categoria, elasticidad=elasticidad)

    persona_bytes = normalizar_orientacion_exif(persona_bytes)
    prenda_normalizada = normalizar_orientacion_exif(prenda_bytes)
    motor = obtener_motor_vto(proveedor, byok_api_key=byok_api_key)
    if hasattr(motor, "garment_photo_type"):
        motor.garment_photo_type = tipo_foto_prenda if tipo_foto_prenda in ("model", "flat-lay") else "model"
    resultado_png = await motor.generar_prueba(
        persona_bytes=persona_bytes,
        prenda_bytes=prenda_normalizada,
        categoria=categoria,
        elasticidad=elasticidad,
    )

    imagen_b64 = base64.b64encode(resultado_png).decode("ascii")
    return ResultadoTryOn(
        version=APP_VERSION,
        proveedor_ia=motor.nombre_proveedor,
        imagen_resultado_base64=imagen_b64,
        recomendacion_talle=rec_talle,
        privacidad_borrado_temporal=VTO_AUTO_BORRAR_TEMPORALES,
    )
