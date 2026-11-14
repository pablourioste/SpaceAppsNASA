# Datos de la Luna: el kit cerrado (v1)

> Revisión completa de las fuentes, 14/11/2026: PDS Geosciences (Diviner, LOLA, LEND, Mini-RF, Lunar Prospector), PGDA (NASA Goddard), USGS y LROC.
> Todo comprobado leyendo las etiquetas de los ficheros, **sin descargarlos**.
> **Cobertura: TODA la Luna**, para que entren todas las misiones (Apolo, Luna, Chang'e, SLIM, CLPS…), los tubos de lava y las regiones de la base del polo sur.
> Es el punto de partida con el que trabajamos hasta el final. Si algo se añade, se apunta aquí.

## 1. El kit: cada variable, de dónde sale fuera y dentro del polo

Hay dos zonas porque algunos productos no llegan al polo. **Zona global** = de 60° N a 60° S. **Zona polar** = de 60° a 90°.

| Variable de la ficha | Zona global | Zona polar | Notas |
|---|---|---|---|
| **Pendiente** (°) a escala L = 800 m [supuesto] | LOLA `ldem_64.img` (relieve, 531 MB, ~470 m) → **la calculamos** | PGDA `LDRM_80S_1000MPP_ADJ_SLP_800M.TIF` (1,5 MB) | Misma escala L en la Luna y en la Tierra |
| **Rugosidad** a L | ídem, calculada | PGDA `…_ROUGH_800M.TIF` (1,5 MB) | |
| **Temperatura media, máxima y mínima** (K) | Diviner **GCP** (casillas de 0,5° ≈ 15 km, temperatura cada 15 min de hora local) | GCP + **Diviner PRP** (~0,5 km, al sur de −76°) | Del GCP: media, máxima y mínima de la columna `tbol` (−9999 = sin dato) |
| **Profundidad del hielo** (m) | El hielo no es estable cerca de la superficie fuera de los polos → "más de 2,87 m" [supuesto físico, verificar] | Diviner PRP `ice_depth` + PGDA `LPSR_80S_20MPP_ADJ.TIF` (sombra permanente, 148 MB) | ⚠️ En el PRP, `−999` = más de 2,87 m (NO es "sin dato"); `0` = hielo en la superficie; **`−1` (no documentado) = las zonas más frías (T máx. 52–99 K) → también hielo en la superficie** [interpretación por los datos, verificar en Paige et al. 2010] |
| **Composición: hierro (FeO, %)** | Lunar Prospector GRS `lpgrs_high1_elem_abundance_2deg.tab` (9,9 MB, casillas de 2°, **global**) | ídem | Trae también Al₂O₃, TiO₂, MgO, CaO, SiO₂, K, Th, U. Unidades [verificar] |
| **Tipo de roca** (clase) | Del FeO: mucho hierro → "mar" (basalto); poco → "tierras altas" (anortosita) [umbral a fijar por Ciencia] | ídem | Para el detalle de las fichas finales: mapa geológico del USGS (224 MB) |
| **Rocas** (%) | Diviner `dgdr_ra_avg_cyl_032_img.img` (88,5 MB, ~950 m) | ❌ **no existe** → vacío | Solo cubre 60° N–60° S |
| **Cuevas** | LROC, lista del atlas de pozos (278 pozos con coordenadas) | ídem | **0 pozos al sur de −80°** (el más cercano, a −78°) |
| *Radar CPR* (extra, **no descargado**) | Mini-RF `global_cpr_32ppd_simp_0c.img` (265 MB, ~950 m) | ídem (cubre −90..90°) | No es variable de la ficha. Solo si se sigue el eje "radar" (enfoque §4): `python scripts/download_moon.py --extras` |
| **Altura del Sol** | se calcula (geometría) | geometría + relieve | |

**Descargado el 14/11/2026: 88 ficheros, 4,4 GB** (`python scripts/download_moon.py`; registro en `data/raw/moon/MANIFEST.csv`).
Revisión del mismo día: se quitaron del kit el radar Mini-RF y el exponente de Hurst de PGDA, porque no dan ninguna variable de la ficha (siguen disponibles con `--extras`).

## 2. Tres formas de conseguir un dato

1. **Descargar entero:** los ficheros pequeños (PGDA de 1,5 MB, Lunar Prospector, lista de pozos) o los que hay que recorrer enteros (Diviner PRP, bandas del GCP).
2. **Leer solo un trozo:** todos los servidores responden `206` (comprobado), así que se puede pedir solo una parte del fichero.
   - Los TIF de PGDA son *Cloud-Optimized GeoTIFF* y `rasterio` lee **solo la ventana** de cada sitio:
     ```python
     import rasterio
     from rasterio.windows import from_bounds
     url = "/vsicurl/https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LPSR_80S_20MPP_ADJ.TIF"
     with rasterio.open(url) as src:          # estereográfica polar, en metros
         zona = src.read(1, window=from_bounds(x0, y0, x1, y1, src.transform))
     ```
   - Los `.img` cilíndricos (LOLA, Mini-RF, Diviner) guardan la imagen fila a fila, de norte a sur. Se pueden pedir **solo las filas de la latitud de cada sitio**.
3. **Leer una tabla web:** la lista de pozos de LROC.

## 3. Revisado y descartado (que nadie pierda tiempo)

| Producto | Por qué no |
|---|---|
| Diviner GDR L3 **por fechas** (`…_2009…`, 1,9 GB) | Una semana cada fichero; los acumulados equivalentes ya están en el kit |
| Diviner GDR L3 temperatura del suelo / CF | Solo 60° N–60° S y no aportan más que el kit (CF: composición, ya cubierta por Lunar Prospector) |
| Diviner GHRM | Solo 70° S–70° N, ficheros de 3,3 GB |
| LEND (neutrones) | Solo cuentas en bruto, ningún mapa hecho |
| LOLA `ldsm` / `ldrm` (pendiente y rugosidad hechas) | La escala no está clara (la etiqueta dice 240 m y 30–120 m). Mejor calcularla nosotros o usar PGDA |
| SLDEM2015 (relieve de 59 m, 2,8 GB) | Más detalle del necesario; `ldem_64` basta para la escala de 800 m |
| Radio Science | Gravedad: no es una variable de la ficha |
| PGDA 104 (relieve de 5 m de las 13 regiones de 2022) | Excesivo para comparar; útil solo para las fichas finales |

## 4. Pendiente

- [ ] **Catálogo de sitios:** ampliar `data/catalogs/target_sites.csv` con todas las misiones (Luna, Surveyor, Chang'e 3/5/6, SLIM, CLPS…) y los pozos/tubos de lava, **con coordenadas de fuente oficial**.
- [ ] **Coordenadas de las 9 regiones del polo sur (NASA 2024).**
- [ ] Ciencia: fijar la escala L (propuesta: 800 m) y el umbral de FeO para "mar" / "tierras altas".
- [ ] Comprobar las unidades de Lunar Prospector (fracción o %).

## Enlaces

- Diviner (GCP, PRP, GDR): https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/
- LOLA, relieve global: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/
- PGDA, polo sur (producto 90): https://pgda.gsfc.nasa.gov/products/90 (ficheros en `https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/`)
- Lunar Prospector, composición: https://pds-geosciences.wustl.edu/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/
- Mini-RF, mosaico global: https://pds-geosciences.wustl.edu/lro/lro-l-mrflro-5-global-mosaic-v1/lromrf_1001/data/32ppd/
- LROC, atlas de pozos: https://lroc.im-ldi.com/atlases/pits/list
- USGS, mapa geológico unificado: https://astrogeology.usgs.gov/search/map/unified_geologic_map_of_the_moon_1_5m_2020
