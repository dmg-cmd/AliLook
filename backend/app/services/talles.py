"""Motor geométrico de estimación de medidas y recomendación de talles."""

from typing import Dict
from app.models.schemas import (
    CategoriaPrenda,
    Complexion,
    ElasticidadTejido,
    MedidasCorporales,
    RangoTalle,
    RecomendacionTalle,
)

# Tabla estándar de referencia (cm) calibrada a tallaje comercial estándar/Latam.
TABLA_TALLES_ESTANDAR: Dict[str, RangoTalle] = {
    "XS": RangoTalle(pecho_cm=84, cintura_cm=68, cadera_cm=88, largo_cm=64),
    "S": RangoTalle(pecho_cm=90, cintura_cm=74, cadera_cm=94, largo_cm=67),
    "M": RangoTalle(pecho_cm=96, cintura_cm=80, cadera_cm=100, largo_cm=70),
    "L": RangoTalle(pecho_cm=102, cintura_cm=86, cadera_cm=106, largo_cm=73),
    "XL": RangoTalle(pecho_cm=108, cintura_cm=92, cadera_cm=112, largo_cm=76),
    "XXL": RangoTalle(pecho_cm=116, cintura_cm=100, cadera_cm=120, largo_cm=79),
}

HOLGURA_POR_ELASTICIDAD: Dict[ElasticidadTejido, float] = {
    ElasticidadTejido.RIGIDO: 2.0,
    ElasticidadTejido.MEDIO: 0.0,
    ElasticidadTejido.ELASTICO: -2.5,
}


def estimar_medidas_corporales(datos: MedidasCorporales) -> Dict[str, float]:
    """Completa pecho, cintura y cadera si el usuario solo ingresó altura y peso."""
    altura_m = datos.altura_cm / 100.0
    imc = datos.peso_kg / (altura_m * altura_m)

    factor_complexion = {
        Complexion.DELGADA: -2.0,
        Complexion.MEDIA: 0.0,
        Complexion.ROBUSTA: 2.5,
    }[datos.complexion]

    # Aproximación antropométrica base calibrada por IMC y altura
    pecho_est = round(54.0 + (imc * 1.85) + (datos.altura_cm - 170.0) * 0.15 + factor_complexion, 1)
    cintura_est = round(38.0 + (imc * 1.95) + (datos.altura_cm - 170.0) * 0.10 + factor_complexion, 1)
    cadera_est = round(58.0 + (imc * 1.80) + (datos.altura_cm - 170.0) * 0.14 + factor_complexion, 1)

    return {
        "pecho_cm": datos.pecho_cm if datos.pecho_cm is not None else pecho_est,
        "cintura_cm": datos.cintura_cm if datos.cintura_cm is not None else cintura_est,
        "cadera_cm": datos.cadera_cm if datos.cadera_cm is not None else cadera_est,
    }


def recomendar_talle(
    datos: MedidasCorporales,
    categoria: CategoriaPrenda,
    elasticidad: ElasticidadTejido = ElasticidadTejido.MEDIO,
    tabla_personalizada: Dict[str, RangoTalle] | None = None,
) -> RecomendacionTalle:
    """Cruza las medidas del usuario con la tabla de talles y retorna la mejor coincidencia."""
    medidas = estimar_medidas_corporales(datos)
    tabla = tabla_personalizada or TABLA_TALLES_ESTANDAR
    holgura = HOLGURA_POR_ELASTICIDAD[elasticidad]

    claves_relevantes = {
        CategoriaPrenda.SUPERIOR: ["pecho_cm", "cintura_cm"],
        CategoriaPrenda.INFERIOR: ["cintura_cm", "cadera_cm"],
        CategoriaPrenda.CUERPO_ENTERO: ["pecho_cm", "cintura_cm", "cadera_cm"],
    }[categoria]

    mejor_talle = "M"
    menor_error = float("inf")
    diferencia_media = 0.0

    for nombre_talle, rango in tabla.items():
        errores = []
        diferencias = []
        for clave in claves_relevantes:
            valor_prenda = getattr(rango, clave, None)
            if valor_prenda is None:
                continue
            valor_efectivo = valor_prenda - holgura
            diff = valor_efectivo - medidas[clave]
            errores.append(abs(diff))
            diferencias.append(diff)

        if not errores:
            continue

        error_promedio = sum(errores) / len(errores)
        diff_prom = sum(diferencias) / len(diferencias)
        # Penaliza levemente si el talle queda más chico que el cuerpo real
        penalizacion = 1.5 if diff_prom < -1.5 else 0.0
        costo = error_promedio + penalizacion
        if costo < menor_error:
            menor_error = costo
            mejor_talle = nombre_talle
            diferencia_media = diff_prom

    if diferencia_media > 2.5:
        ajuste = "holgado"
    elif diferencia_media < -2.0:
        ajuste = "ajustado"
    else:
        ajuste = "justo"

    tiene_medidas_exactas = any(
        v is not None for v in (datos.pecho_cm, datos.cintura_cm, datos.cadera_cm)
    )
    confianza_base = 0.92 if tiene_medidas_exactas else 0.78
    confianza = max(0.45, round(confianza_base - min(menor_error * 0.02, 0.35), 2))

    return RecomendacionTalle(
        talle_recomendado=mejor_talle,
        ajuste_estimado=ajuste,
        confianza=confianza,
        medidas_utilizadas=medidas,
        detalle=(
            f"Talle {mejor_talle} recomendado con ajuste {ajuste} "
            f"(elasticidad: {elasticidad.value})."
        ),
    )
