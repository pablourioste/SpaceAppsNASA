"""CATÁLOGO ÚNICO de los datos del proyecto: qué carpeta es qué, de dónde sale y cómo se usa.

Todo dataset vive en  <DATA>/raw/<cuerpo>/<carpeta>/   (DATA = analogs.paths.DATA)
y este fichero es la única lista de esas carpetas. La usan:
  scripts/importar_datos.py   para saber dónde va cada fichero de un zip o pendrive
  scripts/inventario.py       para decir qué hay, qué falta y escribir <DATA>/LEEME.md
Si añades un dataset: añade una línea aquí (y su descarga en el script de su cuerpo).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    body: str            # moon | mars | earth
    folder: str          # nombre de la carpeta dentro de raw/<body>/
    product: str         # producto oficial
    what: str            # qué contiene, en una frase
    variables: str       # columnas de la ficha que salen de aquí
    resolution: str      # resolución espacial nativa
    time: str            # cómo se trata el tiempo (fijo / climatología / un año…)
    reading: str         # cómo se lee: formato, escala, valores de "sin dato"
    source: str          # web oficial o servicio
    download: str        # cómo se descarga
    size: str            # tamaño aproximado
    processed_by: str    # código que lo convierte en fichas


C = Dataset  # abreviatura para la tabla

DATASETS: list[Dataset] = [
    # ================================================================== TIERRA
    C("earth", "mcd12c1", "MODIS MCD12C1 v061 (2025)",
      "Cubierta del suelo: % de cada clase IGBP (17 clases) en cada celda",
      "máscara: in_mask, env (hielo polar / desierto / árido abierto)", "0,05° (~5,6 km)", "FIJO: un año (2025)",
      "HDF4. SDS 'Land_Cover_Type_1_Percent' (3600×7200×17, uint8, %); índice = clase IGBP (0 agua, 7 matorral abierto, "
      "10 pradera, 15 nieve/hielo, 16 suelo desnudo)", "NASA LP DAAC (Earthdata)",
      "scripts/download_earth.py mask", "1,2 GB", "scripts/build_earth_mask.py"),
    C("earth", "imerg_monthly", "GPM IMERG Final mensual v07 (GPM_3IMERGM)",
      "Lluvia mensual", "precip_mm_year (+ condición de aridez de la máscara)", "0,1° (~11 km)",
      "CLIMATOLOGÍA 2019–2023 (60 meses): media de la tasa × horas del año",
      "HDF5. 'Grid/precipitation' (1, 3600 lon, 1800 lat), mm/h, lat ascendente; negativos = sin dato",
      "NASA GES DISC (Earthdata)", "scripts/download_earth.py mask", "1,1 GB", "build_earth_mask.py → earth.py"),
    C("earth", "srtmgl30", "NASA SRTMGL30 v002",
      "Relieve 30″, de 60° N a 56° S (27 piezas formato GTOPO30)", "elevation_m, slope_deg, roughness_deg",
      "30″ (~0,93 km)", "FIJO (año 2000)",
      "Zip con un .DEM sin cabecera: int16 big-endian, 4800×6000; el nombre da la esquina NO (W020N40); 0 = mar",
      "NASA LP DAAC (Earthdata)", "scripts/download_earth.py dem", "0,26 GB", "src/analogs/earth.py"),
    C("earth", "etopo2022_30s", "NOAA ETOPO 2022 v1, 30″, superficie",
      "Relieve global (incluye el Ártico y la Antártida): rellena lo que SRTMGL30 no cubre",
      "elevation_m, slope_deg, roughness_deg (solo donde no hay SRTMGL30)", "30″ (~0,93 km)", "FIJO",
      "GeoTIFF float32 43200×21600; incluye batimetría (mar < 0): en los polos solo se usa lo que está > 0 m",
      "NOAA NCEI (sin cuenta)", "scripts/download_earth.py dem", "1,6 GB", "src/analogs/earth.py"),
    C("earth", "etopo2022_15s", "NOAA ETOPO 2022 v1, 15″, superficie (piezas de 15°×15°)",
      "Relieve global a ~460 m: MISMA línea base que MOLA 128 px/° (Marte) y LOLA ldem_64 (Luna)",
      "slope_deg, roughness_deg, elevation_m (malla H3: earth_grid.py)", "15″ (~0,46 km)", "FIJO",
      "GeoTIFF float32 3600×3600 por pieza; nombre = esquina superior izquierda (N30E000); incluye "
      "batimetría: solo se usan los píxeles de tierra según MCD12C1", "NOAA NCEI (sin cuenta)",
      "scripts/download_earth.py dem15 (solo las 226 piezas con tierra)", "4,6 GB", "src/analogs/earth_grid.py"),
    C("earth", "myd11c3", "MODIS Aqua MYD11C3 v061",
      "Temperatura de la superficie, mensual, de día (13:30) y de noche (01:30)", "t_mean_K, t_max_K, t_min_K",
      "0,05° (~5,6 km)", "CLIMATOLOGÍA 2019–2023: 12 medias mensuales → media, mes más cálido (día), mes más frío (noche)",
      "HDF4. 'LST_Day_CMG' y 'LST_Night_CMG' uint16 × 0,02 = K; 0 = sin dato",
      "NASA LP DAAC (Earthdata)", "scripts/download_earth.py temp", "4,2 GB", "src/analogs/earth.py"),
    C("earth", "merra2_dust", "NASA MERRA-2 M2TMNXAER v5.12.4 (recorte OPeNDAP)",
      "Espesor óptico de aerosoles a 550 nm: solo polvo (DUEXTTAU) y total (TOTEXTTAU), mensual",
      "dust_aod, dust_aod_max, total_aod", "0,5° × 0,625° (~55 km)",
      "CLIMATOLOGÍA 2019–2023: media anual y mes de más polvo",
      "netCDF4/HDF5 (recortado a 4 variables). 'DUEXTTAU', 'TOTEXTTAU' (1, 361 lat, 576 lon); lat −90…90, lon −180…179,375",
      "NASA GES DISC, servicio OPeNDAP de Earthdata", "scripts/download_earth.py polvo", "~90 MB", "src/analogs/earth.py"),
    C("earth", "ecostress_wps", "ECOSTRESS ECO_L3G_WPS v001",
      "Porcentaje en peso de sílice (SiO₂) de rocas, arena y suelo expuestos: primer mapa mineral de las zonas áridas",
      "silica_wt_pct", "0,01° (~1,1 km), de 53° N a 53° S", "FIJO (media 2023–2024)",
      "GeoTIFF; se agrega a 0,05° con media (rasterio.warp.reproject, Resampling.average)",
      "NASA LP DAAC (Earthdata)", "scripts/download_earth.py silice", "2,5 GB", "src/analogs/earth.py"),
    C("earth", "mod10cm", "MODIS Terra MOD10CM v061",
      "Cobertura de nieve mensual (% de la celda)", "snow_cover_pct, snow_months", "0,05° (~5,6 km)",
      "CLIMATOLOGÍA 2019–2023: % medio anual y nº de meses con más del 50 %",
      "HDF4. 'Snow_Cover_Monthly_CMG' uint8, 0–100 = %; > 100 = códigos (noche, nube, agua, sin dato)",
      "NASA NSIDC (Earthdata)", "scripts/download_earth.py nieve", "~120 MB", "src/analogs/earth.py"),

    # ================================================================== LUNA (docs/06_datos_luna.md)
    C("moon", "diviner_gcp", "LRO Diviner GCP", "Temperatura por casilla y hora local (toda la Luna)",
      "t_mean_K, t_max_K, t_min_K", "0,5° (~15 km)", "MEDIA DE TODA LA MISIÓN por hora local (día lunar típico)",
      "Tablas .tab por bandas de 10° de latitud; columna tbol; −9999 = sin dato", "PDS Geosciences",
      "scripts/download_moon.py", "2,7 GB", "pendiente (falta src/analogs/moon.py)"),
    C("moon", "diviner_prp", "LRO Diviner PRP (polo sur)", "Temperaturas y profundidad del hielo, al sur de −76°",
      "t_mean_K, t_max_K, ice_depth_m", "~0,5 km", "MEDIA DE TODA LA MISIÓN",
      "Tabla .tab; ice_depth −999 = más de 2,87 m (NO es sin dato); 0 = hielo en superficie", "PDS Geosciences",
      "scripts/download_moon.py", "0,6 GB", "pendiente"),
    C("moon", "lola_ldem64", "LRO LOLA LDEM 64 px/°", "Relieve global", "slope_deg, roughness_deg (calculadas)",
      "1/64° (~0,47 km)", "FIJO", "PDS3 .img + .lbl", "PDS Geosciences", "scripts/download_moon.py", "0,5 GB", "pendiente"),
    C("moon", "pgda_south_pole", "NASA PGDA producto 90", "Pendiente y rugosidad a varias escalas, sombra permanente, relieve 80 m (80–90° S)",
      "slope_deg, roughness_deg, ice_depth_m (sombra)", "20 m – 1 km (estereográfica polar)", "FIJO",
      "GeoTIFF (COG), proyección estereográfica polar en metros", "NASA Goddard PGDA", "scripts/download_moon.py",
      "0,35 GB", "pendiente"),
    C("moon", "lunar_prospector_grs", "Lunar Prospector GRS", "Composición: FeO, SiO₂, Al₂O₃, TiO₂, MgO, CaO, K, Th, U",
      "lithology (de FeO), silica_wt_pct (de SiO₂)", "2° (~60 km)", "FIJO (misión 1998–99)",
      "Tabla .tab + .fmt; unidades [verificar]", "PDS Geosciences", "scripts/download_moon.py", "11 MB", "pendiente"),
    C("moon", "diviner_rocks", "LRO Diviner abundancia de rocas", "Rocas en superficie, 60° N–60° S", "rock_abundance_pct",
      "1/32° (~0,95 km)", "FIJO", "PDS3 .img + .lbl", "PDS Geosciences", "scripts/download_moon.py", "85 MB", "pendiente"),
    C("moon", "usgs_geology", "USGS Unified Geologic Map of the Moon", "Mapa geológico (para las fichas finales)",
      "— (detalle)", "1:5M", "FIJO", "Zip GIS (shapefiles)", "USGS Astrogeology", "scripts/download_moon.py", "0,2 GB", "pendiente"),
    C("moon", "lroc_pits", "LROC Pits Atlas", "278 pozos (posibles tubos de lava) con coordenadas", "caves",
      "puntos", "FIJO", "CSV", "LROC (ASU)", "scripts/download_moon.py", "<1 MB", "pendiente"),

    # ================================================================== MARTE (src/analogs/download.py)
    C("mars", "mola_megdr_16ppd", "MGS MOLA MEGDR 16 px/°", "Relieve global", "slope_deg, roughness_deg, elevation_m",
      "1/16° (~3,7 km)", "FIJO", "PDS3 .img int16 big-endian 5760×2880 + .lbl", "PDS Geosciences",
      "scripts/download_data.py mola", "33 MB", "src/analogs/mars.py"),
    C("mars", "mola_megdr_128ppd", "MGS MOLA MEGDR 128 px/° (piezas)", "Relieve fino alrededor de los sitios", "slope_deg (fino)",
      "1/128° (~0,46 km)", "FIJO", "PDS3 .img por piezas", "PDS Geosciences", "scripts/download_data.py mola128", "variable", "src/analogs/mars.py"),
    C("mars", "mola_megdr_polar128", "MGS MOLA polar 128 px/°", "Relieve de los polos", "slope_deg (polos)",
      "~0,46 km", "FIJO", "PDS3 .img", "PDS Geosciences", "scripts/download_data.py mola_polar", "variable", "src/analogs/mars.py"),
    C("mars", "tes_thermal_inertia", "MGS TES inercia térmica", "Inercia térmica de día y de noche + máscaras",
      "thermal_inertia_day_SI, thermal_inertia_night_SI", "1/20° (~3 km)", "FIJO",
      "PDS3 .img int16 big-endian 7200×3600; 0 = sin dato", "PDS Geosciences", "scripts/download_data.py tes", "~0,2 GB", "src/analogs/mars.py"),
    C("mars", "grs_special", "Mars Odyssey GRS/NS", "Flujo de neutrones epitermales (hidrógeno)", "ns_epithermal_cps",
      "0,5°", "FIJO", "Tabla .tab; −99,999 = sin dato", "PDS Geosciences", "scripts/download_data.py grs", "pequeño", "src/analogs/mars.py"),
    C("mars", "grs_elements", "Mars Odyssey GRS elementos", "H₂O, Cl, Fe, Si, K, Th", "grs_*_wt_pct / ppm",
      "5° (~300 km)", "FIJO", "Tabla .tab; 9999,999 = sin dato; sin datos al norte de ~45°", "PDS Geosciences",
      "scripts/download_data.py grs_elements", "pequeño", "src/analogs/mars.py"),
    C("mars", "tes_atmos_my26", "MGS TES atmósfera, año marciano 26", "5,29 millones de medidas: polvo, hielo, T y P de superficie",
      "dust_aod, t_max_K, t_mean_K (aprox.)", "medidas sueltas → malla de 2°", "UN AÑO MARCIANO (MY26), solo ~14 h",
      "Texto .dat; se agrupa en malla de 2° (mars.py)", "PDS Atmospheres (NMSU)", "scripts/download_data.py tes_atmos",
      "0,5 GB", "src/analogs/mars.py"),
    C("mars", "mcs_tsurf_my31", "MRO MCS temperatura de superficie (MY31)", "Temperatura de día (~15 h) y de noche (~03 h)",
      "t_mean_K, t_min_K", "perfiles → malla", "UN AÑO MARCIANO (MY31), muestreado", "CSV pequeños (src/analogs/mcs.py)",
      "PDS Atmospheres (NMSU)", "scripts/download_data.py mcs_tsurf", "variable", "src/analogs/mcs.py"),
    C("mars", "swim2_ice", "SWIM 2 (hielo somero)", "Probabilidad de hielo a poca profundidad", "ice_depth_m (aprox.)",
      "variable", "FIJO", "ver src/analogs/download.py", "Planetary Science Institute", "scripts/download_data.py swim",
      "variable", "pendiente"),
]

BODY_ALIASES = {"moon": "moon", "luna": "moon", "mars": "mars", "marte": "mars", "earth": "earth", "tierra": "earth"}


def by_body(body: str) -> list[Dataset]:
    return [d for d in DATASETS if d.body == body]


def known_folders() -> dict[str, str]:
    """carpeta → cuerpo (para colocar ficheros sueltos de un zip)."""
    return {d.folder: d.body for d in DATASETS}
