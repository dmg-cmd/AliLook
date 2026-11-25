# Estándar de Versionado Base-10

El proyecto utiliza versionado decimal en base 10 con formato `Mayor.Medio.Inferior`:

* **Inferior (`0..9`):** Se incrementa en `1` en cada revisión o ajuste menor. Al llegar a `10`, vuelve a `0` e incrementa el número **Medio** en `1`.
* **Medio (`0..9`):** Representa hitos funcionales o entregas (por ejemplo `0.1.0`, `0.2.0`). Al llegar a `10`, vuelve a `0` e incrementa el número **Mayor** en `1`.
* **Mayor:** Cambios arquitectónicos mayores o lanzamientos principales (`1.0.0`, `2.0.0`).

## Automatización

Ejecuta desde la raíz del proyecto:

```powershell
.\scripts\versionar.ps1 -Descripcion "Descripción breve del cambio"
```

El script actualiza automáticamente:
1. `VERSION`
2. `backend/app/core/config.py`
3. `README.md`
4. `docs/MANUAL_USUARIO.md`
5. `docs/HISTORIAL.md`
