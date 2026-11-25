"""ConfiguraciÃ³n central del backend Proyecto Ali."""

import os
from pathlib import Path

APP_NAME = "AliLook - Probador Virtual VTO"
APP_VERSION = "0.3.4"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
WEIGHTS_FASHN = BASE_DIR.parent / "models" / "fashn-vton-1.5" / "weights" / "model.safetensors"

# Proveedor de IA activo: usa "fashn_local" si existen los pesos, sino "simulado"
_proveedor_defecto = "fashn_local" if WEIGHTS_FASHN.exists() else "simulado"
VTO_PROVIDER = os.getenv("VTO_PROVIDER", _proveedor_defecto).strip().lower()
VTO_CLOUD_URL = os.getenv("VTO_CLOUD_URL", "").strip()
VTO_CLOUD_TOKEN = os.getenv("VTO_CLOUD_TOKEN", "").strip()
VTO_AUTO_BORRAR_TEMPORALES = os.getenv("VTO_AUTO_BORRAR_TEMPORALES", "true").lower() == "true"

# Configuración de Failover Multi-Proveedor y BYOK
VTO_FAILOVER_TIMEOUT_S = float(os.getenv("VTO_FAILOVER_TIMEOUT_S", "18.0"))
VTO_REMOTE_ENDPOINTS_URL = os.getenv("VTO_REMOTE_ENDPOINTS_URL", "").strip()
VTO_COMMUNITY_ENDPOINTS = [
    u.strip() for u in os.getenv("VTO_COMMUNITY_ENDPOINTS", "").split(",") if u.strip()
]
VTO_BYOK_GEMINI_KEY = os.getenv("VTO_BYOK_GEMINI_KEY", "").strip()
VTO_FAILOVER_CADENA = [
    x.strip().lower()
    for x in os.getenv(
        "VTO_FAILOVER_CADENA",
        "fashn_local,nube_comunitaria,byok_gemini,simulado",
    ).split(",")
    if x.strip()
]

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
