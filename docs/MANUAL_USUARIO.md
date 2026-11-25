# Manual de Usuario y Puesta en Marcha — AliLook

**Versión:** `0.3.4`

Este manual explica cómo instalar el servidor en tu PC con Windows, conectar tu teléfono Android y aprovechar todas las funciones de **AliLook**.

---

## 1. Instalación del servidor (Backend en Windows)

Abre PowerShell en la carpeta raíz del proyecto y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

> **Nota sobre GPU NVIDIA:** Para ejecutar **FASHN VTON v1.5** de forma local en tu GPU (ej. NVIDIA RTX 3080 de 8 GB), instala PyTorch con soporte CUDA desde el sitio oficial de PyTorch (100 % gratuito y open source) y coloca los pesos del modelo en `models/fashn-vton-1.5/weights/model.safetensors`. Si los pesos no están presentes, el servidor inicia automáticamente en modo `simulado` para pruebas de flujo.

---

## 2. Iniciar el servidor

Tienes dos formas de iniciar el backend:

* **Opción recomendada (Windows):** haz doble clic en `iniciar_servidor.bat` en la raíz del proyecto y elige la interfaz de red (Wi-Fi o USB) en el menú interactivo.
* **Opción manual (PowerShell):**

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

El parámetro `--host 0.0.0.0` habilita el acceso desde tu teléfono Android dentro de la misma red Wi-Fi.

---

## 3. Conectar desde Android

### Con la app nativa **AliLook**
1. Abre **AliLook** en tu celular.
2. Presiona **Buscar PC** en la barra superior:
   * Si el celular está conectado por cable USB con `adb reverse tcp:8000 tcp:8000`, se conectará a `http://127.0.0.1:8000`.
   * Si está en el mismo Wi-Fi, detectará automáticamente la IP de tu PC mediante descubrimiento UDP (`puerto 8001`).
3. También puedes escribir manualmente la URL (ej. `http://192.168.1.50:8000`) y presionar **Ir**.

### Desde un navegador web móvil
Abre Chrome o Firefox en tu celular y entra a `http://<IP-DE-TU-PC>:8000`.

---

## 4. Guía de uso de la aplicación

### A. Perfiles cifrados con biometría (Bóveda Multi-Perfil)
En la app Android **AliLook**, la tarjeta superior permite guardar perfiles independientes (por ejemplo, distintos integrantes de la familia):
1. Toma o elige tu foto frontal y completa tu altura, peso y medidas opcionales (pecho, cintura, cadera, hombros).
2. Escribe un nombre para el perfil y presiona **Guardar**.
3. La foto y las medidas se cifran con **AES-256-GCM** usando una clave no exportable del **Android Keystore**.
4. Para usar o borrar un perfil guardado, selecciónalo en la lista y confirma con tu huella, rostro o PIN.
5. **Respaldo portátil (`.alilook`):** usa **Exportar (.alilook)** para guardar un archivo cifrado con contraseña (incluye foto, medidas y todo el armario del perfil) y **Importar (.alilook)** para restaurarlo en otro teléfono.

### B. Pestaña **⚡ Prueba Rápida**
Pensada para probar una prenda en menos de 30 segundos:
1. **Tu foto frontal:** usa **Cámara (5s)** para disparar con temporizador o **Galería** para elegir una foto existente.
2. **Prenda:** selecciona una imagen desde tu celular o **comparte una imagen directamente hacia AliLook** desde Chrome, tu galería o cualquier app usando el menú *Compartir* de Android.
3. Ajusta categoría (`Superior`, `Inferior`, `Cuerpo entero`) y tipo de tejido (`Rígido`, `Medio`, `Elástico`).
4. Marca el consentimiento de privacidad y presiona **Probar prenda**.
5. En el visor a pantalla completa verás el resultado junto con el **talle recomendado** y el botón opcional **Guardar en Armario**.

### C. Pestaña **👕 Armario Digital**
1. **Agregar prenda:** elige una foto, asigna un nombre y etiquetas (`Categoría`, `Tejido`, `Color`, `Clima`, `Ocasión`) y presiona **Recortar y guardar en Armario**. El backend recortará el fondo automáticamente y la prenda quedará guardada de forma cifrada dentro del perfil activo.
2. **Filtros combinables:** busca por texto y combina filtros de categoría, color, clima y ocasión al mismo tiempo.
3. **Probar ahora:** toca **Probar ahora** en cualquier prenda del armario para cargarla en *Prueba Rápida*.

### D. Caché local de resultados
Cuando repites exactamente la misma combinación (misma foto base, misma prenda y mismas medidas), **AliLook** recupera el resultado al instante desde la caché cifrada local (`· ⚡ Caché`) sin volver a procesar en la GPU. Puedes vaciarla en cualquier momento con el botón **Limpiar caché local de pruebas**.

---

## 5. Cambiar de motor de IA (Local ↔ Nube)

Crea un archivo `.env` en `backend/` (o define variables de entorno):

```env
VTO_PROVIDER=failover
# Opciones disponibles:
# - failover     (conmutación automática: fashn_local -> nube comunitaria -> BYOK -> simulado)
# - fashn_local  (FASHN VTON v1.5 en GPU NVIDIA local)
# - nube_http    (reenvía la petición a un servidor GPU remoto)
# - byok_gemini  (nivel gratuito de Google AI Studio con clave propia)
# - simulado     (pruebas rápidas sin cargar pesos en VRAM)
VTO_FAILOVER_TIMEOUT_S=18.0
VTO_REMOTE_ENDPOINTS_URL=
VTO_COMMUNITY_ENDPOINTS=
VTO_BYOK_GEMINI_KEY=
VTO_CLOUD_URL=https://tu-servidor-gpu.ejemplo/api/v1/try-on
VTO_CLOUD_TOKEN=tu_token_opcional
```
