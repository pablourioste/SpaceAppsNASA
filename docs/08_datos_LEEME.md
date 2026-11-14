# LEEME: carpeta de datos del proyecto «Earth Analogs for Moon & Mars» (NASA Space Apps 2026)

> **Este fichero va dentro de la carpeta de datos** (`SpaceAppsData/LEEME.md`). Lo genera
> `scripts/inventario.py --leeme` a partir de `docs/08_datos_LEEME.md` del repositorio, con el inventario real al final.
> Está escrito para personas **y para asistentes de IA (Claude)**: la sección 1 es un prompt que hay que seguir.

---

## 0. Qué es esto, en 5 líneas

1. El proyecto busca **lugares de la Tierra que se parecen físicamente** a sitios de la **Luna** y de **Marte** (bases, aterrizajes) para probar allí ruedas, perforación, navegación, etc.
2. Los datos de satélite (NASA, NOAA, USGS) se descargan **una vez** en `raw/`, se convierten en **fichas** (tablas con una fila por sitio o por celda de la Tierra) en `processed/`, y el buscador o la app comparan fichas.
3. El parecido es un **índice de 0 a 100**: cada variable se compara **en sus unidades físicas** con una tolerancia (`configs/variables.yaml`) y se promedia con los pesos de la prueba elegida (`configs/pruebas.yaml`).
4. El **código** está en el repositorio de GitHub (`https://github.com/marcantich/SpaceAppsNASA`). Los **datos** están en esta carpeta, **fuera de git** (pesan GB).
5. Hoy la Tierra está **procesada**. La Luna y Marte están **descargadas** pero falta convertirlas en fichas (ver la sección 10).

---

## 1. Instrucciones para el asistente (prompt)

**Eres** un asistente que ayuda a un equipo de la NASA Space Apps a procesar y consultar estos datos. Sigue estas reglas:

1. **Antes de nada**, localiza el repositorio (la carpeta con `src/analogs/` y `scripts/`) y esta carpeta de datos. Comprueba que el código ve esta carpeta:
   ```powershell
   .venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from analogs.paths import DATA; print(DATA)"
   ```
   Debe imprimir la ruta de esta carpeta. Si no, aplica la sección 2.2.
2. **Nunca modifiques ni borres nada de `raw/`.** Es lo descargado, tal cual. Todo lo derivado va a `interim/` o `processed/` y se puede regenerar.
3. **Nunca subas datos a git** ni los copies dentro del repositorio. **Nunca leas, copies ni compartas `~/.netrc`** (contiene la contraseña de Earthdata de su dueño).
4. **Ejecuta siempre con el Python del entorno del repo**: `.venv\Scripts\python.exe` (Windows) o `.venv/bin/python`. En **Windows PowerShell 5.1 no existe `&&`**: un comando por línea.
5. **Sigue el orden de la sección 4.** Si un paso falla porque falta un dataset, mira la sección 10 y el catálogo (`src/analogs/catalog.py`); **no inventes datos ni coordenadas**.
6. **No cambies tolerancias, pesos ni umbrales** (`configs/*.yaml`, constantes de `scripts/build_earth_mask.py`) sin que lo pida el usuario: los decide el equipo de Ciencia. Todos están marcados `[supuesto]`.
7. **Convenciones obligatorias**: temperaturas en **K**; longitudes de **−180 a 180 este**; latitud **planetocéntrica** en la Luna y Marte, **geodésica WGS84** en la Tierra; unidades SI salvo que la columna diga otra cosa (`_pct`, `_mm_year`, `_deg`).
8. Cuando digas algo no comprobado, márcalo **[verificar]**; un valor elegido por el equipo, **[supuesto]**.
9. Tras procesar, **verifica con los números de referencia de la sección 7** y dile al usuario qué cuadra y qué no.
10. Si el usuario quiere **compartir datos**, usa `scripts/pack_data.py` (zips) y, en el otro ordenador, `scripts/importar_datos.py` (sección 8).

---

## 2. Mapa de la carpeta

```
SpaceAppsData/                      ← esta carpeta (DATA)
├── LEEME.md                        ← este fichero
├── raw/                            PASO 1 · tal cual se descarga. NO TOCAR
│   ├── earth/<carpeta>/            un dataset por carpeta (lista: sección 9)
│   │   └── MANIFEST.csv            qué fichero, de dónde, cuántos bytes, cuándo
│   ├── moon/<carpeta>/  + MANIFEST.csv
│   └── mars/<carpeta>/  + MANIFEST.csv
├── interim/                        PASO 2 · mallas intermedias (.npz): se pueden borrar y regenerar
│   ├── earth_mask_005deg.npz       máscara y lluvia en la malla de 0,05°
│   └── earth_cmg_h3r5.npz          a qué hexágono H3 pertenece cada píxel (caché)
└── processed/                      PASO 3 · FICHAS (.parquet): lo que usan el buscador y la app
    ├── fichas_tierra_005deg.parquet  una fila por píxel de tierra de 0,05° (~5,6 km)  ← la más fina
    ├── fichas_tierra_h3r5.parquet    una fila por hexágono H3 res 5 (~17 km, igual área)
    ├── earth_mask_h3r5.parquet       máscara por hexágono (y _h3r4, ~45 km)
    └── fichas_objetivos_<cuerpo>.parquet   una fila por sitio de la Luna / Marte (cuando se generen)
```

### 2.1 Dónde tiene que estar esta carpeta

El código (`src/analogs/paths.py`) la busca en este orden:
1. Variable de entorno `ANALOGS_DATA_DIR`.
2. (Windows) la misma variable guardada con `setx`, aunque la terminal se abriera antes.
3. **`C:\Users\<tú>\SpaceAppsData`** (o `~/SpaceAppsData`). **Lo más fácil: copiar la carpeta ahí y no configurar nada.**
4. `<repo>/data` (antiguo).

### 2.2 Si el código no la encuentra

```powershell
setx ANALOGS_DATA_DIR "D:\ruta\a\SpaceAppsData"     # y abrir una terminal NUEVA
```
**No la pongas dentro de OneDrive/Dropbox**: bloquean los ficheros mientras sincronizan.

---

## 3. Preparar el ordenador (una vez)

```powershell
git clone https://github.com/marcantich/SpaceAppsNASA.git
cd SpaceAppsNASA
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q          # debe pasar todo
```
Solo para **descargar** de Earthdata (no para usar estos datos): cuenta gratuita en https://urs.earthdata.nasa.gov, fichero `~/.netrc` con
`machine urs.earthdata.nasa.gov login <usuario> password <contraseña>` y, en *Applications → Authorized Apps*, aprobar **NASA GESDISC DATA ARCHIVE**.

---

## 4. Cómo se procesa (en orden)

| Paso | Comando | Lee | Escribe | Qué hace |
|---|---|---|---|---|
| 0 | `scripts\inventario.py --leeme` | todo | `LEEME.md` | Dice qué hay y qué falta; reescribe este fichero |
| 1a | `scripts\download_earth.py [grupo…]` | Earthdata / NOAA | `raw/earth/` | Descarga la Tierra. Grupos: `mask dem temp polvo silice nieve`. Se puede relanzar |
| 1b | `scripts\download_moon.py` · `scripts\download_data.py` | PDS, PGDA… | `raw/moon/` · `raw/mars/` | Descargan la Luna y Marte |
| 1c | `scripts\importar_datos.py <zip/carpeta>` | pendrive | `raw/`, `processed/` | En vez de descargar: copia lo que te pasen (sección 8) |
| 2 | `scripts\build_earth_mask.py` | `mcd12c1`, `imerg_monthly` | `interim/earth_mask_005deg.npz`, `processed/earth_mask_h3r*.parquet`, `outputs/maps/earth_mask.png` | Decide **dónde se busca**: desiertos, hielo polar y zonas áridas sí; mar, bosques, cultivos, ciudades, humedales no |
| 3 | `scripts\build_earth_features.py` | todo `raw/earth/` + máscara | `processed/fichas_tierra_005deg.parquet`, `processed/fichas_tierra_h3r5.parquet` | Calcula **todas las variables** en la malla de 0,05° y las agrega a hexágonos |
| 4 | `scripts\build_mars_features.py` | `raw/mars/` | `processed/fichas_objetivos_mars.parquet` | Variables en cada sitio de Marte (`data/catalogs/target_sites.csv`) |
| 5 | `scripts\buscar.py [--malla h3r5]` | `processed/` | `outputs/validation/busqueda_*.csv` | **Buscador en la terminal**: valores a mano, parecidos a un punto de la Tierra o a un sitio de la Luna/Marte, estadísticas |

Todos se lanzan **desde la raíz del repositorio** con `.venv\Scripts\python.exe scripts\<script>.py`.
Pasos 2 y 3: unos 2–4 minutos y ~10 GB de RAM en total.

### 4.1 La máscara (paso 2), exactamente
Por cada celda de 0,05° (MCD12C1 da el % de cada clase):
- **tierra** = 100 − %agua ≥ 50
- **hielo polar** = %nieve/hielo permanente ≥ 50
- **desierto** = %suelo desnudo ≥ 50 (sin mirar la lluvia: coladas de lava, salares)
- **árido abierto** = %(desnudo + matorral abierto + pradera) ≥ 60 **y** lluvia < 350 mm/año
- **se queda** = tierra **y** (hielo polar **o** desierto **o** árido abierto). Un hexágono se queda si ≥ 25 % de su tierra está dentro.

---

## 5. Tiempo y escala: las reglas

- **Unidad de comparación de la Tierra**: el **píxel de 0,05°** (~5,6 km en el ecuador, más estrecho hacia los polos) o el **hexágono H3 res 5** (~17 km, todos de igual área). Los sitios de la Luna y Marte se miden en una ventana de ~10 km (decisión 006).
- **No se baja de 0,05°** en la búsqueda global: la temperatura y la cubierta del suelo no existen más finas en estos productos, y los objetivos son más gruesos (temperatura lunar 15 km, composición 60–300 km). El detalle fino (30 m – 1 km) se usa **solo** en los 2–3 sitios finalistas.
- **Relieve**: pendiente calculada a **30″ (~0,93 km)** y luego promediada; misma escala que MOLA 64 px/° en Marte.
- **Tiempo**: lo FIJO (relieve, composición, cubierta del suelo) se usa tal cual. Lo de CLIMA se reduce a **condiciones típicas de 2019–2023** (no récords):
  - `t_mean_K` = media de los 12 meses de (día + noche)/2 · `t_max_K` = mes más cálido de día (13:30) · `t_min_K` = mes más frío de noche (01:30).
  - Igual que en la Luna (media de la misión por hora local) y Marte (un año marciano).

---

## 6. Columnas de las fichas de la Tierra

| Columna | Unidad | Qué es | Fuente (carpeta en `raw/earth/`) |
|---|---|---|---|
| `pixel` / `cell` | — | id: fila·7200+columna de la malla 0,05° / id del hexágono H3 | — |
| `lat`, `lon` | ° | centro (WGS84; lon −180…180 E) | — |
| `in_mask` | bool | dentro de la máscara de búsqueda | `mcd12c1`, `imerg_monthly` |
| `env`, `env_name` | — | 0 fuera · 1 hielo polar · 2 desierto · 3 árido abierto | `mcd12c1` |
| `kept_frac` | 0–1 | (hexágonos) fracción de su tierra dentro de la máscara | `mcd12c1` |
| `precip_mm_year` | mm/año | lluvia media 2019–2023 | `imerg_monthly` |
| `elevation_m` | m | altura media | `srtmgl30` (60° N–56° S) + `etopo2022_30s` (polos) |
| `slope_deg` | ° | pendiente media a 30″ | ídem |
| `roughness_deg` | ° | RMS de la pendiente | ídem |
| `t_mean_K`, `t_max_K`, `t_min_K` | K | temperatura de superficie típica (sección 5) | `myd11c3` |
| `lst_months` | nº | meses de la climatología con dato (12 = completo) | `myd11c3` |
| `dust_aod`, `dust_aod_max` | — | espesor óptico del polvo (550 nm): media anual / mes máximo | `merra2_dust` |
| `total_aod` | — | espesor óptico de todos los aerosoles | `merra2_dust` |
| `silica_wt_pct` | % peso | sílice de la superficie expuesta (53° N–53° S) | `ecostress_wps` |
| `snow_cover_pct`, `snow_months` | %, nº | nieve media anual / meses con > 50 % | `mod10cm` |
| `sun_elev_max_deg` | ° | altura máxima del Sol en el año (geometría, horizonte plano) | calculada |

Las variables que entran en el índice son las que están en `configs/variables.yaml` con dato en **los dos** lados (objetivo y Tierra).

---

## 7. Comprobaciones (números de referencia)

| Qué | Valor esperado |
|---|---|
| Píxeles de tierra (0,05°) | **8.510.253**, de ellos **4.301.556** dentro de la máscara |
| Hexágonos H3 res 5 con tierra | **586.229**, de ellos **201.850** dentro |
| Máscara (en área) | hielo polar 10,1 % · desierto 13,7 % · árido abierto 10,7 % · **total 34,4 %** de la tierra emergida |
| Análogos conocidos dentro (`outputs/validation/earth_mask_known_analogs.csv`) | **15 de 20**. Fuera, y es lo esperado: Río Tinto, Ries, Sudbury, Lonar (análogos de geología en zonas con vegetación) y Kilauea |
| `buscar.py` → [2] → lat −24.1, lon −70.0 (Atacama) | los primeros son desiertos cálidos y secos (Sáhara argelino, Namib, costa de Perú, Baja California, Omán) con índice > 90 |
| `buscar.py` → [1] → t_mean −63 °C, t_max 270 K, lluvia 0 (tipo Marte) | **ninguno pasa de ~61**: la Tierra no reproduce ese frío medio con esos máximos (es un resultado, no un error) |

---

## 8. Compartir datos con el equipo

| Qué | Cómo | Tamaño |
|---|---|---|
| **Solo las fichas** (basta para usar `buscar.py`) | `scripts\pack_data.py tables --out E:\` → `tables_processed.zip` | ~0,3 GB |
| Datos brutos de un cuerpo | `scripts\pack_data.py earth --out E:\` (o `moon`, `mars`) → un zip por grupo de datasets | ver sección 9 |
| En el ordenador que recibe | `scripts\importar_datos.py E:\ --dry-run` y luego sin `--dry-run` (acepta un zip, una carpeta de zips o una carpeta) | — |
| Código | `git pull` / `git push` | — |

**Nunca** se comparte `~/.netrc`, ni el `.venv` (no funciona en otro ordenador: se crea con la sección 3).
Todos los datos son públicos (NASA, NOAA, USGS): se pueden compartir dentro del equipo sin restricciones.

---

## 9. Inventario de esta carpeta (generado)

<!-- INVENTARIO -->

---

## 10. Pendiente

- **Luna**: escribir `src/analogs/moon.py` (Diviner GCP/PRP, LOLA a ~1 km, Lunar Prospector, pozos) → `fichas_objetivos_moon.parquet`. Faltan las **coordenadas de las 9 regiones del polo sur** (NASA 2024) en `data/catalogs/target_sites.csv`: sacarlas de los polígonos oficiales, no a ojo.
- **Marte**: ejecutar `build_mars_features.py` con los datos importados; decidir si la pendiente se calcula con MOLA 128 px/° remuestreado a ~0,93 km (misma escala que la Tierra).
- **Tierra**: litología (GLiM) y permafrost (ESA CCI), fuera de Earthdata.
- **Calidad de datos de la Tierra a revisar**:
  - la lluvia de IMERG sobrestima en desiertos hiperáridos (Atacama da 80–260 mm/año; lo real son unos pocos mm) [verificar];
  - la sílice de ECOSTRESS solo es fiable en roca/suelo desnudo: en zonas basálticas con vegetación sale alta (Kilauea ~76 %, cuando el basalto tiene ~50 %) [verificar]. Úsala solo dentro de la máscara (desiertos);
  - el polvo de MERRA-2 es un reanálisis de ~55 km: sirve como contexto regional, no para distinguir sitios cercanos.
- **Ciencia**: fijar tolerancias, pesos y umbrales de la máscara; decidir qué máscara usa cada prueba (superficie vs. geología).
