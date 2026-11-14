# data/ — los datos

```
data/
├── catalogs/    pequeños, hechos a mano. SÍ van a git.
│   ├── target_sites.csv     sitios OBJETIVO de la Luna y Marte (lo que buscas)
│   └── known_analogs.csv    análogos terrestres YA conocidos (para validar y marcarlos)
├── raw/         PASO 1: tal cual se descargan. NUNCA se modifican.  NO van a git.
│   ├── earth/
│   ├── moon/
│   └── mars/
├── interim/     PASO 2: recortados y en malla común. Se pueden borrar y regenerar.  NO van a git.
└── processed/   PASO 3: las FICHAS, una fila por sitio o hexágono.  NO van a git.
                 fichas_tierra.parquet · fichas_objetivos.parquet
```

El paso 4 (el índice para la app) no está aquí: va a [`app/data/`](../app/README.md).

## Reglas

1. **Los ficheros grandes NO se suben a git.** El `.gitignore` ya ignora `raw/`, `interim/` y `processed/`. Se comparten por el Drive del equipo: _[enlace aquí]_.
2. Si el repo está en OneDrive, **no metas GBs dentro de la carpeta sincronizada**. Mejor una carpeta local fuera del repo, definiendo la variable de entorno `ANALOGS_DATA_DIR` (ver [`src/analogs/paths.py`](../src/analogs/paths.py)).
3. **Todo dataset descargado se apunta en el inventario de abajo.** Hace falta para reproducir el trabajo y para la entrega, que pide citar los datos usados.
4. Unidades SI y nombres de columna **exactamente** como en [`configs/variables.yaml`](../configs/variables.yaml).
5. Longitudes en −180..180 este; latitudes planetocéntricas.

## Catálogos

| Fichero | Contenido | Estado |
|---|---|---|
| `target_sites.csv` | 30 sitios: 9 regiones candidatas del polo sur lunar (NASA 2024), aterrizajes de Apolo, Chang'e 4, Chandrayaan-3, Shackleton y 12 sitios de Marte | Coordenadas aproximadas; **faltan las de las 9 regiones lunares** (sacarlas de los polígonos oficiales de NASA) |
| `known_analogs.csv` | 20 análogos terrestres conocidos | Coordenadas aproximadas [verificar]; falta la columna `dimension` (qué reproduce cada uno) |

## Cuentas necesarias (gratuitas, cada uno la suya)

| Portal | Para descargar | Cuenta |
|---|---|---|
| NASA Earthdata | Datos de la Tierra (MODIS, ASTER, EMIT, NASADEM…) | Earthdata Login |
| Copernicus Data Space | Sentinel-1/2, Copernicus DEM | Sí |
| EODMS (CSA) | RADARSAT-1, RCM | Sí |
| JAXA G-Portal | Nieve, precipitación, temperatura | Sí |
| PDS (NASA) | Luna y Marte (Diviner, LOLA, Mini-RF, MOLA…) | **No** |

**Las contraseñas nunca van en el código ni en git.**

## Inventario de datasets

Estado: **identificado** = existe y sabemos dónde está · **descargado** · **procesado** (ya está en las fichas).

| Dataset | Cuerpo | Variable | Resolución | Formato | Dónde | Estado | Quién |
|---|---|---|---|---|---|---|---|
| Diviner PRP sur (`dlre_prp_south.tab`) | Luna | `temp_avg` (K, 2 cm), `temp_max` (K), `ice_depth` (m) | malla triangular, 2,88 M triángulos | tabla de texto, ~605 MB | PDS Geosciences → LRO → Diviner → PRP | identificado | |
| Diviner PCP (diurnal / seasonal) | Luna | temperaturas polares | [verificar] | [verificar] | PDS Geosciences → Diviner → PCP | identificado | |
| LOLA GDR / SLDEM | Luna | relieve → pendiente, rugosidad | según producto | [verificar] | PDS Geosciences / Lunar ODE | identificado | |
| Mini-RF | Luna | radar (CPR) | [verificar] | [verificar] | PDS Geosciences (página caída el 13/11) | por comprobar | |
| MOLA MEGDR 16 ppd (`megt90n000eb`, `megc90n000eb`) → `raw/mars/mola_megdr_16ppd/` | Marte | topography (m, radius − areoid) + shots per cell | 16 px/deg (~3.7 km) | binary `.img` + PDS3/PDS4 labels, ~33 MB each | PDS Geosciences → MGS → MOLA → MEGDR (PDS4 bundle) | descargado | |
| TES thermal inertia (`global_ti_{day,night}_2007` + masks) → `raw/mars/tes_thermal_inertia/` | Marte | thermal inertia (J m⁻² K⁻¹ s⁻½) | [see label] | binary `.img` + PDS3 `.lbl` | PDS Geosciences → MGS → TES → Thermal Inertia Maps | descargado | |
| GRS special products (NS/HEND neutron flux, 2002) → `raw/mars/grs_special/` | Marte | epithermal / thermal / fast neutron flux | [see label] | `.tab` text + labels | PDS Geosciences → Odyssey → GRS → Special Products | descargado | |
| GRS element maps, smoothed 5°×5° → `raw/mars/grs_elements/` | Marte | H₂O, Cl, Fe, Si, K, Th (wt%/ppm), K/Th | 5°×5° | `.tab` text + labels | PDS Geosciences → Odyssey → GRS → Element concentration maps | descargado | |
| MOLA-HRSC blend | Marte | relieve | ~200 m [verificar] | [verificar] | PDS / Mars ODE | identificado | |
| `NASADEM_HGT` v001 | Tierra | relieve | 1″ (~30 m) | [verificar] | Earthdata (LP DAAC) | identificado | |
| `MOD11C3` v061 | Tierra | temperatura de superficie mensual | 0,05° | HDF | Earthdata (LP DAAC) | identificado | |
| `MOD21A2` v061 | Tierra | temperatura de superficie, 8 días | 1 km | HDF | Earthdata (LP DAAC) | identificado | |
| `AG100` v003 | Tierra | emisividad ASTER (aproximación de la mineralogía) | 100 m | HDF5 | Earthdata (LP DAAC) | identificado | |
| `EMITL2BMIN` v001 | Tierra | minerales (zonas áridas) | 60 m | [verificar] | Earthdata (LP DAAC) | identificado | |
| `MCD19A2CMG` v061 | Tierra | aerosoles / polvo | 0,05°, diario | HDF | Earthdata (LP DAAC) | identificado | |
| Sentinel-1 GRD | Tierra | radar en banda C | ~10 m | [verificar] | Earthdata (ASF) / Copernicus Data Space | identificado | |
| ESA CCI Permafrost | Tierra | permafrost, capa activa | ~1 km [verificar] | [verificar] | ESA Open Science Catalog [verificar] | por buscar | |
