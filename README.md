# AliLook (Proyecto Ali) — Probador Virtual de Ropa con IA y Armario Digital

**Versión actual:** `0.3.5`

Aplicación **100 % Open Source (FOSS)** de probador virtual de ropa (*Virtual Try-On*) y armario digital cifrado para **Android** y **PC (Windows / Linux)**, sin registros obligatorios, sin publicidad, sin marcas de agua ni suscripciones.

Funciona conectando la app móvil **AliLook** a un servidor local con GPU NVIDIA (por ejemplo, **RTX 3080 de 8 GB** ejecutando **FASHN VTON v1.5**) o a un servidor remoto intercambiable mediante una API REST en **FastAPI**.

---

## Características principales

* **Prueba Rápida (< 30 s):** toma una foto con temporizador de 5 s (o elige una de la galería), carga una prenda y obtén la simulación visual junto con la recomendación de talle.
* **Importación directa (*Share Intent* en Android):** comparte cualquier imagen o captura desde el navegador o la galería directamente hacia **AliLook** para probarla al instante.
* **Armario Digital cifrado con filtros combinables:** guarda prendas ya recortadas automáticamente (`rembg`) con etiquetas de **categoría**, **tejido**, **color**, **clima** y **ocasión**, y combínalas con búsqueda en tiempo real.
* **Bóveda multi-perfil AES-256-GCM + Biometría:** almacena múltiples perfiles familiares (foto base y medidas corporales) y su armario cifrados en **Android Keystore**, desbloqueables únicamente con huella, rostro o PIN del dispositivo.
* **Caché local cifrada de resultados:** reutiliza al instante pruebas ya generadas (misma foto base + prenda + medidas) sin volver a consumir GPU ni red.
* **Failover Multi-Proveedor y BYOK opcional:** conmutación automática con timeouts cortos ante errores `429`/`503`/`504` entre GPU local (`fashn_local`), nodos comunitarios (con lista dinámica JSON remota), API gratuita BYOK (`byok_gemini`) y modo `simulado`.
* **Exportación portátil cifrada (`.alilook`):** respalda y migra perfiles completos (foto, medidas y armario) protegidos con contraseña mediante `PBKDF2WithHmacSHA256` + `AES-256-GCM`.
* **Motor geométrico de talles:** estima o utiliza medidas reales (altura, peso, complexión, pecho, cintura, cadera, hombros) para recomendar el talle (`XS` a `XXL`) y nivel de ajuste (`holgado`, `justo`, `ajustado`).
* **Descubrimiento automático en red local:** el botón **Buscar PC** detecta automáticamente el servidor por cable USB (`127.0.0.1:8000`) o por Wi-Fi mediante difusión UDP (`puerto 8001`).

---

## Documentación del proyecto

* [Manual de Usuario y Puesta en Marcha](docs/MANUAL_USUARIO.md) — Instalación, inicio del servidor, uso desde Android, Armario Digital, bóveda cifrada y **cómo conseguir modelos/APIs gratuitas**.
* [Arquitectura del Sistema](docs/ARQUITECTURA.md) — Flujo de procesamiento, patrón adaptador VTO y diseño de módulos.
* [Historial de Cambios](docs/HISTORIAL.md) — Registro cronológico de versiones.
* [Estándar de Versionado](docs/VERSIONADO.md) — Reglas de versionado decimal en base 10 (`Mayor.Medio.Inferior`).

---

## Estructura del repositorio

```text
Proyecto Ali/
├── android/                # Aplicación nativa Android (Kotlin + WebView + Android Keystore)
├── backend/                # Servidor FastAPI (Python 3.12 + CUDA)
│   ├── app/
│   │   ├── adapters/       # Motores VTO intercambiables (simulado, fashn_local, nube_http)
│   │   ├── core/           # Configuración central
│   │   ├── models/         # Esquemas Pydantic
│   │   ├── services/       # Talles, recorte de fondo (rembg) y descubrimiento UDP
│   │   ├── static/         # Interfaz móvil (Prueba Rápida + Armario Digital)
│   │   └── main.py         # API REST v1
│   ├── tests/              # Pruebas unitarias (pytest)
│   └── requirements.txt
├── docs/                   # Documentación técnica, manuales e historial
├── scripts/                # Automatización (versionar.ps1)
├── iniciar_servidor.bat    # Lanzador rápido en Windows con selección de IP
├── VERSION                 # Fuente única de versión (0.3.5)
└── README.md
```

---

## Requisitos mínimos

* **Python 3.12+**
* **GPU NVIDIA** con 8 GB de VRAM (para inferencia local con *FASHN VTON v1.5*) o modo `simulado` para pruebas de flujo sin GPU.
* **Android 8.0+** (para la app nativa **AliLook**) o cualquier navegador móvil en la misma red Wi-Fi.

## Inicio rápido en Windows

```powershell
# 1. Crear entorno virtual e instalar dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 2. Iniciar el servidor (o ejecutar iniciar_servidor.bat)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Pruebas unitarias

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests
```
