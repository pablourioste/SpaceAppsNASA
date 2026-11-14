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

> **Luna:** el plan completo (variables → fichero → cómo, y lo descartado) está en [`docs/06_datos_luna.md`](../docs/06_datos_luna.md).
> ✅ **Kit de la Luna v1 DESCARGADO** (14/11/2026): 88 ficheros, 4,4 GB, 0 errores, con `python scripts/download_moon.py` (se quitaron Mini-RF y el exponente de Hurst: no son variables de la ficha). Qué se bajó y de dónde: [`raw/moon/MANIFEST.csv`](raw/moon/MANIFEST.csv). Huellas para comparar: `raw/moon/LISTADO_marc.csv`.
>
> ✅ **Mars kit v1 DOWNLOADED** (14/11/2026): 125 files, 1.95 GB, 0 errors, with `python scripts/download_data.py` (MOLA 16 ppd + 6 tiles of 128 ppd, TES thermal inertia, GRS, TES atmosphere MY26). What was downloaded and from where: [`raw/mars/MANIFEST.csv`](raw/mars/MANIFEST.csv). Fingerprints to compare: `raw/mars/LISTADO_adria.csv`.

Estado: **identificado** = existe y sabemos dónde está · **descargado** · **procesado** (ya está en las fichas).

| Dataset | Cuerpo | Variable | Resolución | Formato | Dónde | Estado | Quién |
|---|---|---|---|---|---|---|---|
| Diviner PRP sur (`dlre_prp_south.tab`) | Luna | `temp_avg` (K, a 2 cm), `temp_max` (K, superficie), `ice_depth` (m). ⚠️ `ice_depth` = 0 → hielo estable en la superficie; **−999 → solo estable a más de 2,87 m (NO es "sin dato")** | malla triangular de ~0,5 km, de ~76° S al polo (600 × 600 km) | tabla de texto, 605 MB, 2,88 M filas | PDS Geosciences → LRO → Diviner → PRP | identificado (formato comprobado) | |
| Diviner PCP (diurnal / seasonal) | Luna | temperaturas polares | [verificar] | [verificar] | PDS Geosciences → Diviner → PCP | identificado | |
| ~~Diviner GDR L3~~ (`dgdr_ra_…cyl…`, `dgdr_tbol_avg_pols_…`) | Luna | rocas, temperaturas por fecha | — | `.img` de 1,9 GB (cilíndricos) / 29 MB (polares) | PDS Geosciences → Diviner → GDR_L3 | ❌ **DESCARTADO:** el mapa de rocas solo cubre 80° N–80° S (no llega al polo sur) y cada fichero es una sola fecha. Los polares solo traen temperaturas por fecha, que ya tenemos mejor en el PRP | |
| LOLA DEM polar sur (`ldem_75s_240m` 29 MB · `ldem_80s_80m` 115 MB · `ldem_85s_20m` 460 MB) | Luna | relieve | 240 / 80 / 20 m | PDS3 `.img` + `.lbl`, estereográfica polar | PDS Geosciences → `lola_gdr/polar/img/` | identificado (tamaños comprobados) | |
| LOLA pendiente (`ldsm_75s_240m` 29 MB · `ldsm_85s_40m` 115 MB) | Luna | pendiente (°) = DN·0,0015 + 45 | 240 / 40 m | PDS3 `.img`, entero de 16 bits | ídem | identificado. ⚠️ La etiqueta dice a la vez "línea base 240 m" y "30–120 m" [verificar] → para comparar con la Tierra, **mejor calcularla nosotros desde el DEM** | |
| LOLA rugosidad (`ldrm_75s_240m` 29 MB · `ldrm_85s_40m` 115 MB) | Luna | rugosidad (m, desviación estándar) = DN·0,001; sin dato = −32768 | 240 / 40 m | ídem | ídem | identificado | |
| Mini-RF | Luna | radar (CPR) | [verificar] | [verificar] | PDS Geosciences (página caída el 13/11) | por comprobar | |

| MOLA MEGDR 128 ppd tiles (`megt…hb` topography 130 MB · `megc…hb` shots per cell 65 MB) → `raw/mars/mola_megdr_128ppd/` | Marte | relieve (slope/roughness at ~463 m) + QC of interpolated cells | 128 px/° (~463 m), 16 tiles of 44°×90° | PDS3/PDS4 `.img` | PDS Geosciences → MGS → MOLA → MEGDR (PDS4 bundle, `meg128/`) | **descargado: 6 tiles with Mars target sites** (00n090, 00n270, 44n000, 44n090, 44n270, 88n180, ~1.2 GB). The other 10 later (ROADMAP 5.6). ⚠️ Many cells near the equator are interpolated: check `megc` | |
| MOLA-HRSC blend | Marte | relieve | ~200 m [verificar] | [verificar] | [verificar] | por buscar | |
| MOLA MEGDR 16 ppd (`megt90n000eb`, `megc90n000eb`) → `raw/mars/mola_megdr_16ppd/` | Marte | topography (m, radius − areoid) + shots per cell | 16 px/deg (~3.7 km) | binary `.img` + PDS3/PDS4 labels, ~33 MB each | PDS Geosciences → MGS → MOLA → MEGDR (PDS4 bundle) | descargado | |
| TES thermal inertia (`global_ti_{day,night}_2007` + masks) → `raw/mars/tes_thermal_inertia/` | Marte | thermal inertia (J m⁻² K⁻¹ s⁻½) | [see label] | binary `.img` + PDS3 `.lbl` | PDS Geosciences → MGS → TES → Thermal Inertia Maps | descargado | |
| GRS special products (NS/HEND neutron flux, 2002) → `raw/mars/grs_special/` | Marte | epithermal / thermal / fast neutron flux | [see label] | `.tab` text + labels | PDS Geosciences → Odyssey → GRS → Special Products | descargado | |
| GRS element maps, smoothed 5°×5° → `raw/mars/grs_elements/` | Marte | H₂O, Cl, Fe, Si, K, Th (wt%/ppm), K/Th | 5°×5° | `.tab` text + labels | PDS Geosciences → Odyssey → GRS → Element concentration maps | descargado | |
| TES IR retrievals, Mars Year 26 (Montabone et al.) → `raw/mars/tes_atmos_my26/` | Marte | column dust OD (9.3 µm), water-ice OD (12.1 µm), surface temperature (K), surface pressure (Pa). **Daytime only (~14 h local time)**: 5.29 M retrievals, Ls 0–360 | individual retrievals (~3 km footprint), 12 files × 30° Ls | fixed-width text `.dat` + PDS4 `.xml`, ~490 MB | PDS Atmospheres → MGS → TES → Atmospheric IR and VIS Derived Data | descargado | |
| `NASADEM_HGT` v001 | Tierra | relieve | 1″ (~30 m) | [verificar] | Earthdata (LP DAAC) | identificado | |
| `MOD11C3` v061 | Tierra | temperatura de superficie mensual | 0,05° | HDF | Earthdata (LP DAAC) | identificado | |
| `MOD21A2` v061 | Tierra | temperatura de superficie, 8 días | 1 km | HDF | Earthdata (LP DAAC) | identificado | |
| `AG100` v003 | Tierra | emisividad ASTER (aproximación de la mineralogía) | 100 m | HDF5 | Earthdata (LP DAAC) | identificado | |
| `EMITL2BMIN` v001 | Tierra | minerales (zonas áridas) | 60 m | [verificar] | Earthdata (LP DAAC) | identificado | |
| `MCD19A2CMG` v061 | Tierra | aerosoles / polvo | 0,05°, diario | HDF | Earthdata (LP DAAC) | identificado | |
| Sentinel-1 GRD | Tierra | radar en banda C | ~10 m | [verificar] | Earthdata (ASF) / Copernicus Data Space | identificado | |
| ESA CCI Permafrost | Tierra | permafrost, capa activa | ~1 km [verificar] | [verificar] | ESA Open Science Catalog [verificar] | por buscar | |
