# scripts/ — lo que se ejecuta

| Script | Qué hace | Estado |
|---|---|---|
| `make_mock_data.py` | Llena `app/data/` con **datos falsos** (mismo formato que los reales) y enseña un ejemplo del motor | ✅ funciona |
| `download_moon.py` | Descarga el **kit de datos de la Luna** (`docs/06_datos_luna.md`) a `data/raw/moon/` y escribe `MANIFEST.csv`. Se puede relanzar: reanuda y salta lo que ya está. `--list` enseña el plan | ✅ funciona |
| `list_data.py` | Hace la **lista** de lo que tienes en una carpeta de datos (ruta, tamaño, huella SHA-256) → `LISTADO_<nombre>.csv`, que sí va a git. Sirve para comparar descargas entre compañeros | ✅ funciona |
| `run_pipeline.py` | Flujo completo con datos reales: APIs → fichas → `app/data/` → validación | ⏳ se para en el paso 1 (pendiente) |

Se ejecutan desde la raíz del repo: `python scripts/make_mock_data.py`.
La lógica va en `src/analogs/`; aquí solo se llama a esa lógica en orden.
Si un script descarga datos, se apunta en el inventario de [`data/README.md`](../data/README.md).
