# scripts/ — lo que se ejecuta

Se ejecutan **desde la raíz del repo**, con el Python del entorno y un comando por línea (PowerShell 5.1 no tiene `&&`):
`.venv\Scripts\python.exe scripts\<script>.py`. La lógica va en `src/analogs/`; aquí solo se llama en orden.

**Datos**: todo se lee y escribe en la carpeta de datos (`src/analogs/paths.py`: `ANALOGS_DATA_DIR` o `~/SpaceAppsData`),
con la estructura `raw/<earth|moon|mars>/<carpeta>/`, `interim/`, `processed/`.
Qué carpeta es qué: **`src/analogs/catalog.py`** (catálogo único). Guía completa (también para Claude): [`docs/08_datos_LEEME.md`](../docs/08_datos_LEEME.md).

## 0 · Gestionar los datos
| Script | Qué hace | Estado |
|---|---|---|
| `inventario.py [--leeme]` | Qué datasets hay y cuáles faltan, GB, filas de cada tabla. Con `--leeme` escribe `<DATA>/LEEME.md` | ✅ |
| `importar_datos.py <zip/carpeta> [--dry-run]` | Coloca en su sitio los datos de un pendrive (zip, carpeta de zips o carpeta) | ✅ |
| `pack_data.py <earth\|moon\|mars\|tables> --out <carpeta>` | Hace los zips para pasar datos (`tables` = solo las fichas, ~0,3 GB) | ✅ |
| `list_data.py` | Lista con huella SHA-256 de una carpeta de datos → `LISTADO_<nombre>.csv` (para comparar descargas) | ✅ |

## 1 · Descargar
| Script | Qué hace | Estado |
|---|---|---|
| `download_earth.py [mask dem temp polvo silice nieve] [--list]` | **Tierra** desde Earthdata/NOAA → `raw/earth/` (necesita `~/.netrc`) | ✅ |
| `download_moon.py [--list]` | **Luna** (`docs/06_datos_luna.md`) → `raw/moon/` | ✅ |
| `download_data.py [mola tes grs …] [--list]` | **Marte** (datasets en `src/analogs/download.py`) → `raw/mars/` | ✅ |

## 2 · Procesar → fichas
| Script | Qué hace | Estado |
|---|---|---|
| `build_earth_mask.py` | Máscara de la Tierra (desiertos, hielo, zonas áridas sí; mar, bosques, cultivos no) + mapa | ✅ |
| `build_earth_features.py` | Fichas de la Tierra: `processed/fichas_tierra_005deg.parquet` (0,05°) y `_h3r5` (~17 km) | ✅ |
| `build_mars_features.py` | Fichas de los sitios de Marte → `processed/fichas_objetivos_mars.parquet` | ⏳ borrador (tarea 3.5) |
| *(falta)* `build_moon_features.py` | Fichas de los sitios de la Luna | ❌ por hacer |

## 3 · Usar
| Script | Qué hace | Estado |
|---|---|---|
| `buscar.py [--malla h3r5]` | **Buscador en la terminal**: valores a mano, parecidos a un punto de la Tierra o a un sitio de la Luna/Marte, estadísticas | ✅ |
| `make_mock_data.py` | Llena `app/data/` con **datos falsos** para la app | ✅ |
| `build_comparator_data.py` | Adapta `app/data` al comparador | ✅ |
| `run_pipeline.py` | Flujo completo con datos reales → `app/data/` | ⏳ pendiente |
