"""Pruebas unitarias para el motor geométrico de talles y adaptadores VTO."""

import asyncio
from io import BytesIO
from PIL import Image

from app.adapters.factory import obtener_motor_vto
from app.models.schemas import (
    CategoriaPrenda,
    Complexion,
    ElasticidadTejido,
    MedidasCorporales,
)
from app.services.talles import estimar_medidas_corporales, recomendar_talle


def test_estimar_medidas_completa_campos():
    datos = MedidasCorporales(altura_cm=175, peso_kg=72, complexion=Complexion.MEDIA)
    medidas = estimar_medidas_corporales(datos)
    assert "pecho_cm" in medidas
    assert "cintura_cm" in medidas
    assert "cadera_cm" in medidas
    assert 80 < medidas["pecho_cm"] < 120


def test_recomendar_talle_con_medidas_exactas():
    datos = MedidasCorporales(
        altura_cm=175,
        peso_kg=72,
        pecho_cm=96,
        cintura_cm=80,
        cadera_cm=100,
    )
    rec = recomendar_talle(datos, categoria=CategoriaPrenda.SUPERIOR)
    assert rec.talle_recomendado == "M"
    assert rec.ajuste_estimado == "justo"
    assert rec.confianza >= 0.85


def test_recomendar_talle_185cm_o_metros_88kg():
    rec_cm = recomendar_talle(
        MedidasCorporales(altura_cm=185, peso_kg=88),
        categoria=CategoriaPrenda.SUPERIOR,
    )
    rec_m = recomendar_talle(
        MedidasCorporales(altura_cm=1.85, peso_kg=88),
        categoria=CategoriaPrenda.SUPERIOR,
    )
    assert rec_cm.talle_recomendado == "XL"
    assert rec_m.talle_recomendado == "XL"


def test_adaptador_simulado_genera_png():
    img_persona = BytesIO()
    Image.new("RGB", (200, 400), color=(200, 200, 200)).save(img_persona, format="PNG")
    img_prenda = BytesIO()
    Image.new("RGBA", (120, 120), color=(30, 144, 255, 255)).save(img_prenda, format="PNG")

    motor = obtener_motor_vto("simulado")
    salida = asyncio.run(
        motor.generar_prueba(
            persona_bytes=img_persona.getvalue(),
            prenda_bytes=img_prenda.getvalue(),
            categoria=CategoriaPrenda.SUPERIOR,
            elasticidad=ElasticidadTejido.MEDIO,
        )
    )
    assert len(salida) > 100
    img_res = Image.open(BytesIO(salida))
    assert img_res.size == (200, 400)
