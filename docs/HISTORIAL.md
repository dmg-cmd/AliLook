# Historial de Cambios

Todas las versiones siguen el estándar de versionado decimal en base 10 (`Mayor.Medio.Inferior`).

## [0.1.0] - 2026-11-24
### Agregado
* Estructura inicial del proyecto para Android + Backend local en Windows.
* Documentación técnica y de usuario en `docs/` (`ARQUITECTURA.md`, `MANUAL_USUARIO.md`, `HISTORIAL.md`, `VERSIONADO.md`) y `README.md`.
* Backend en Python (FastAPI) con:
  * Motor geométrico de recomendación de talles (`backend/app/services/talles.py`).
  * Servicio de recorte automático de fondo con respaldo open source (`backend/app/services/fondo.py`).
  * Patrón adaptador intercambiable para modelos VTO (`simulado`, `fashn_local`, `nube_http`).
* Vista web móvil ligera (`backend/app/static/index.html`) para pruebas inmediatas desde Android vía Wi-Fi.
* Script de versionado automático `scripts/versionar.ps1`.

## [0.1.1] - 2026-11-24
### Cambios
* Agrega iniciar_servidor.bat y aplicación Android nativa instalada vía USB.


## [0.1.2] - 2026-11-24
### Cambios
* Agrega menú interactivo de selección de IP/adaptador en iniciar_servidor.bat.


## [0.1.3] - 2026-11-24
### Cambios
* Agrega descubrimiento automático por UDP en red local y botón Buscar PC en Android.


## [0.1.4] - 2026-11-24
### Cambios
* Corrige superposición con la barra de estado en Android usando WindowInsets.


## [0.1.5] - 2026-11-24
### Cambios
* Activa FASHN VTON v1.5 en RTX 3080, corrige rotación EXIF, agrega cámara con temporizador 5s y visor a pantalla completa.


## [0.1.6] - 2026-11-24
### Cambios
* Soporta altura en metros o cm (con coma o punto) y desactiva caché en la vista móvil.


## [0.1.7] - 2026-11-24
### Cambios
* Agrega bóveda cifrada AES-256-GCM en Android Keystore con desbloqueo biométrico/PIN.


## [0.1.8] - 2026-11-24
### Cambios
* Mejora respaldo hacia cámara nativa con aviso de temporizador cuando se usa Wi-Fi HTTP.


## [0.1.9] - 2026-11-24
### Cambios
* Activa segmentation_free=False y num_timesteps=30 en FASHN VTON para respetar la silueta real del usuario.


## [0.2.0] - 2026-11-24
### Cambios
* Preservación corporal (segmentation_free=True), calibración de talles a XL (1,85m/88kg) y versión visible en cabecera.


## [0.2.1] - 2026-11-24
### Cambios
* Agrega campos opcionales de medidas corporales (pecho, cintura, cadera, hombros) guardados en la bóveda cifrada.


## [0.2.2] - 2026-11-24
### Cambios
* Agrega soporte multi-perfil familiar con nombre, cifrado AES-256-GCM y desbloqueo biométrico/PIN.


## [0.2.3] - 2026-11-24
### Cambios
* Renombra la aplicación a AliLook e integra el ícono oficial adaptativo en Android.


## [0.2.4] - 2026-11-25
### Cambios
* Separa Prueba Rápida y Armario Digital con filtros combinables, recorte automático y Share Intent en Android


## [0.2.5] - 2026-11-25
### Cambios
* Agrega caché local cifrada de resultados Try-On con límite LRU/FIFO y limpieza manual


## [0.2.6] - 2026-11-25
### Cambios
* Actualiza README.md y MANUAL_USUARIO.md completos para publicación en GitHub


## [0.2.7] - 2026-11-25
### Cambios
* Agrega failover multi-proveedor VTO con timeouts cortos, endpoints comunitarios remotos y soporte BYOK opcional


## [0.2.8] - 2026-11-25
### Cambios
* Agrega exportación e importación portátil cifrada (.alilook) con PBKDF2 y AES-256-GCM y actualiza documentación


## [0.2.9] - 2026-11-25
### Cambios
* Corrige composición RGBA sobre blanco y segmentation_free en FASHN VTON, y persiste estado de sesión y último perfil en Android


## [0.3.0] - 2026-11-25
### Cambios
* Simplifica la pantalla principal con botón único de Perfil colapsable y flujo directo de elección de prenda


## [0.3.1] - 2026-11-25
### Cambios
* Agrega soporte de tema Sistema, Claro y Oscuro en la interfaz móvil


## [0.3.2] - 2026-11-25
### Cambios
* Agrega selector de tipo de foto de prenda (model vs flat-lay) y restaura segmentation_free=True en FASHN VTON


## [0.3.3] - 2026-11-25
### Cambios
* Reemplaza details/summary por botón desplegable en Motor de IA para compatibilidad total en Android WebView


## [0.3.4] - 2026-11-25
### Cambios
* Agrega detección automática de color dominante y nombre sugerido al guardar prendas en el Armario Digital

