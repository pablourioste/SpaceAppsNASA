# scripts/ — lo que se ejecuta

| Script | Qué hace | Estado |
|---|---|---|
| `make_mock_data.py` | Llena `app/data/` con **datos falsos** (mismo formato que los reales) y enseña un ejemplo del motor | ✅ funciona |
| `download_moon.py` | Descarga el **kit de datos de la Luna** (`docs/06_datos_luna.md`) a `data/raw/moon/` y escribe `MANIFEST.csv`. Se puede relanzar: reanuda y salta lo que ya está. `--list` enseña el plan | ✅ funciona |
| `download_data.py` | Downloads the **Mars kit** (MOLA, TES, GRS, TES atmosphere; datasets in `src/analogs/download.py`) to `data/raw/mars/` and writes `MANIFEST.csv` (same format as `download_moon.py`). Re-runnable: skips what is already there. `--list` shows the datasets; `python scripts/download_data.py mola128` downloads just one | ✅ works |
| `pack_data.py` | Packs `data/raw/<body>/` into one zip per dataset (paths kept, unzip into `data/raw/`), e.g. to attach to a GitHub Release | ✅ works |
| `build_mars_features.py` | Extracts the variables at each Mars target site → `data/processed/fichas_objetivos_mars.parquet` | ⏳ draft (task 3.5) |
| `list_data.py` | Hace la **lista** de lo que tienes en una carpeta de datos (ruta, tamaño, huella SHA-256) → `LISTADO_<nombre>.csv`, que sí va a git. Sirve para comparar descargas entre compañeros | ✅ funciona |
| `run_pipeline.py` | Flujo completo con datos reales: APIs → fichas → `app/data/` → validación | ⏳ se para en el paso 1 (pendiente) |

Se ejecutan desde la raíz del repo: `python scripts/make_mock_data.py`.
La lógica va en `src/analogs/`; aquí solo se llama a esa lógica en orden.
Si un script descarga datos, se apunta en el inventario de [`data/README.md`](../data/README.md).
