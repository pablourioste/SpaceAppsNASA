"""La malla de fichas de la TIERRA: todas las variables en hexágonos H3, MISMO formato que Marte.

    .venv\\Scripts\\python.exe scripts\\build_earth_grid.py            # H3 res 6 (por defecto)
    .venv\\Scripts\\python.exe scripts\\build_earth_grid.py --res 5    # H3 res 5

Es el equivalente de src/analogs/mars_grid.py (Adrià) para la Tierra:
  - una fila por celda H3 de TODO el planeta (mar = NaN), columna `h3` (texto), `lat`, `lon` y una
    columna float32 por variable → data/processed/earth_h3r<res>.parquet
  - mismo método raster → celda (ROADMAP 3.5): paso bajo = media ponderada por área; paso alto
    (plano restado) SOLO para la rugosidad; mediana ponderada para la pendiente.
  - después, scripts/build_earth_grid.py lo escribe en binario con analogs.export.write_grid_binary
    → app/data/tierra/ (docs/07_card_grid_binary_format.md), igual que app/data/marte/.

Tamaño de celda (H3 es una malla angular: el mismo nivel mide distinto en cada cuerpo):
  Marte res 5 ≈ 9,1 km entre lados · Luna res 5 ≈ 4,7 km · Tierra res 5 ≈ 17 km · Tierra res 6 ≈ 6,5 km.
  La Tierra res 6 es la más parecida a los ~9 km de Marte (y está entre Marte y la Luna).

Por variable (fuente → celda):
  slope_deg, roughness_deg, elevation_m  relieve a 15″ (~460 m, ETOPO 2022: misma línea base que MOLA 128 px/°
                                         y LOLA ldem_64) si está descargado; si no, 30″ (~0,93 km: SRTMGL30
                                         + ETOPO 30″ en los polos) y se avisa. Solo píxeles de tierra.
  t_*, precip, polvo, sílice, nieve,     malla 0,05° de src/analogs/earth.py (climatologías 2019–2023) →
  máscara (in_mask, env, kept_frac)      media ponderada por ÁREA DE INTERSECCIÓN (cada píxel se parte en
                                         3×3 subpíxeles, como TES en Marte)
  land_frac                              fracción de la celda que es tierra (MCD12C1)
  sun_elev_max_deg                       fórmula con la latitud del centro (oblicuidad 23,44°)
"""
from __future__ import annotations

import time

import h3.api.basic_int as h3i
import numpy as np
import pandas as pd
from h3ronpy.vector import cells_to_coordinates, coordinates_to_cells

from .earth import (EARTH_OBLIQUITY_DEG, EARTH_RADIUS_M, LAT, LON, N_LAT, N_LON, RAW_EARTH, RES,
                    compute_fields, load_mask)
from .mars_grid import Grid, finish_topography, weighted_median_groups, wrap180
from .paths import PROCESSED


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def to_cells(lat: np.ndarray, lon: np.ndarray, res: int) -> np.ndarray:
    """H3 de muchos puntos a la vez (h3ronpy, vectorizado; mismo resultado que h3-py)."""
    return np.asarray(coordinates_to_cells(np.ascontiguousarray(lat, dtype=np.float64),
                                           np.ascontiguousarray(wrap180(lon), dtype=np.float64), res)).astype(np.uint64)


class EarthGrid(Grid):
    """La misma clase de acumuladores que mars_grid.Grid, pero a la resolución que se pida."""

    def __init__(self, res: int) -> None:          # noqa: D107 (no llama a Grid.__init__: otra resolución)
        self.res = res
        cells = np.fromiter((c for r in h3i.get_res0_cells() for c in h3i.cell_to_children(r, res)), dtype=np.uint64)
        cells.sort()
        self.cells = cells
        coords = cells_to_coordinates(cells)
        self.lat = np.asarray(coords.column("lat")).astype(np.float64)
        self.lon = np.asarray(coords.column("lng")).astype(np.float64)
        self.n = len(cells)
        self.sums = {}
        self.median_parts = {}


# --------------------------------------------------------------------------------------
# Relieve: pendiente (mediana ponderada), rugosidad (paso alto), elevación
# --------------------------------------------------------------------------------------

def _accumulate_dem(grid: EarthGrid, ids, z, gx, gy, lat, lon, w) -> None:
    """Igual que mars_grid._accumulate_topography, con el radio de la Tierra."""
    uniq, inv = np.unique(ids, return_inverse=True)
    gidx = grid.index(uniq)
    clat, clon = grid.lat[gidx][inv], grid.lon[gidx][inv]
    x = EARTH_RADIUS_M * np.cos(np.deg2rad(clat)) * np.deg2rad(wrap180(lon - clon))
    y = EARTH_RADIUS_M * np.deg2rad(lat - clat)
    gi = gidx[inv]
    for name, val in [("W", w), ("Sx", w * x), ("Sy", w * y), ("Sz", w * z), ("Sxx", w * x * x),
                      ("Syy", w * y * y), ("Sxy", w * x * y), ("Sxz", w * x * z), ("Syz", w * y * z),
                      ("Sgx", w * gx), ("Sgy", w * gy), ("Sgg", w * (gx * gx + gy * gy)),
                      ("Wmeas", w), ("Welev", w), ("Selev", w * z)]:
        grid.add(name, gi, val)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    med = weighted_median_groups(inv, slope, w, len(uniq))
    grid.add_median("slope", gidx, med, np.bincount(inv, weights=w, minlength=len(uniq)))


def _process_block(grid: EarthGrid, z: np.ndarray, lat_rows: np.ndarray, lon_cols: np.ndarray,
                   land_cmg: np.ndarray, halo_top: int, halo_bottom: int) -> None:
    """Un bloque de relieve (filas con 1 fila de halo arriba/abajo) → sumas de la malla."""
    dim = abs(lat_rows[1] - lat_rows[0])
    step = np.deg2rad(dim) * EARTH_RADIUS_M
    gy = -np.gradient(z, axis=0) / step                                            # d z / d norte
    gx = np.gradient(z, axis=1) / (step * np.clip(np.cos(np.deg2rad(lat_rows)), 1e-3, None))[:, None]
    cut = slice(halo_top, z.shape[0] - halo_bottom)
    z, gx, gy, lat_rows = z[cut], gx[cut], gy[cut], lat_rows[cut]
    # solo píxeles de TIERRA (máscara MCD12C1 a 0,05°) y con dato en el píxel y sus vecinos
    ri = np.clip(((90 - lat_rows) / RES).astype(int), 0, N_LAT - 1)
    ci = np.clip(((wrap180(lon_cols) + 180) / RES).astype(int), 0, N_LON - 1)
    keep = land_cmg[ri][:, ci] & np.isfinite(z) & np.isfinite(gx) & np.isfinite(gy)
    if not keep.any():
        return
    rr, cc = np.nonzero(keep)
    lat, lon = lat_rows[rr], lon_cols[cc]
    _accumulate_dem(grid, to_cells(lat, lon, grid.res), z[rr, cc].astype(np.float64), gx[rr, cc], gy[rr, cc],
                    lat, lon, np.cos(np.deg2rad(lat)))


def process_relief(grid: EarthGrid, land_cmg: np.ndarray) -> str:
    """Relieve → sumas. Devuelve la descripción de la fuente usada (para index.json)."""
    import rasterio
    from rasterio.windows import Window

    tiles15 = sorted((RAW_EARTH / "etopo2022_15s").glob("*.tif"))
    needed = 0                                    # piezas de 15°×15° con tierra (las que baja download_earth.py dem15)
    for top in range(90, -90, -15):
        for west in range(-180, 180, 15):
            r0, c0 = int((90 - top) / RES), int((west + 180) / RES)
            needed += bool(land_cmg[r0:r0 + 300, c0:c0 + 300].any())
    if tiles15 and len(tiles15) < needed:
        log(f"⚠️  Relieve 15″ incompleto ({len(tiles15)}/{needed} piezas): se usa 30″ hasta que acabe la descarga")
        tiles15 = []
    if tiles15:
        log(f"Relieve 15″ (~460 m): {len(tiles15)} piezas ETOPO 2022")
        for k, t in enumerate(tiles15, 1):
            try:
                with rasterio.open(t) as src:
                    z = src.read(1).astype(np.float64)
                    tr = src.transform
            except Exception as e:  # noqa: BLE001 — pieza a medias
                log(f"  ✗ {t.name}: {type(e).__name__} (se salta)")
                continue
            lat_rows = tr.f + (np.arange(z.shape[0]) + 0.5) * tr.e
            lon_cols = tr.c + (np.arange(z.shape[1]) + 0.5) * tr.a
            # sin halo entre piezas: el gradiente del borde es de un solo lado (error de 1 fila, despreciable)
            _process_block(grid, z, lat_rows, lon_cols, land_cmg, 0, 0)
            if k % 25 == 0:
                log(f"  {k}/{len(tiles15)}")
        return "NOAA ETOPO 2022 15″ (~460 m baseline, same as MOLA 128 px/deg and LOLA ldem_64)"

    log("⚠️  No hay relieve a 15″ (download_earth.py dem15): se usa 30″ (~0,93 km) → pendientes más suaves que en Marte/Luna")
    from .earth import _read_srtm30_tile
    for t in sorted((RAW_EARTH / "srtmgl30").glob("*.zip")):
        dem, g = _read_srtm30_tile(t)
        lat_rows = g["uly"] - g["dim"] * np.arange(dem.shape[0])
        lon_cols = g["ulx"] + g["dim"] * np.arange(dem.shape[1])
        _process_block(grid, dem.astype(np.float64), lat_rows, lon_cols, land_cmg, 0, 0)
    tif = next((RAW_EARTH / "etopo2022_30s").glob("*.tif"), None)
    if tif is not None:                                     # polos: lo que SRTMGL30 no cubre
        with rasterio.open(tif) as src:
            dim = src.transform.a
            for top, bottom in ((90.0, 60.0), (-56.0, -90.0)):
                r0, r1 = int(round((90 - top) / dim)), int(round((90 - bottom) / dim))
                z = src.read(1, window=Window(0, r0, src.width, r1 - r0)).astype(np.float64)
                z[z <= 0] = np.nan
                lat_rows = 90 - dim * (np.arange(r0, r1) + 0.5)
                lon_cols = -180 + dim * (np.arange(src.width) + 0.5)
                _process_block(grid, z, lat_rows, lon_cols, land_cmg, 0, 0)
    return "NASA SRTMGL30 + NOAA ETOPO 2022 30″ (~0.93 km baseline; Mars/Moon use ~460 m)"


# --------------------------------------------------------------------------------------
# Campos de 0,05° → celda (área de intersección con 3×3 subpíxeles)
# --------------------------------------------------------------------------------------

def accumulate_cmg(grid: EarthGrid, fields: dict[str, np.ndarray], land: np.ndarray, sub: int = 3,
                   chunk: int = 120) -> None:
    """Media ponderada por área de cada campo 0,05° dentro de cada celda (como accumulate_fine_raster
    de Marte). También acumula el área total (W_all) y la de tierra (W_land) → land_frac."""
    offs = (np.arange(sub) + 0.5) / sub - 0.5
    for r0 in range(0, N_LAT, chunk):
        r1 = min(N_LAT, r0 + chunk)
        lat_s = (LAT[r0:r1, None] - offs[None, :] * RES).ravel()           # subfilas
        lon_s = (LON[:, None] + offs[None, :] * RES).ravel()               # subcolumnas
        LA, LO = np.meshgrid(lat_s, lon_s, indexing="ij")
        ids = to_cells(LA.ravel(), LO.ravel(), grid.res)
        uniq, inv = np.unique(ids, return_inverse=True)
        gidx = grid.index(uniq)
        w = np.cos(np.deg2rad(LA.ravel()))
        pix = lambda a: np.repeat(np.repeat(a[r0:r1], sub, axis=0), sub, axis=1).ravel()  # noqa: E731
        is_land = pix(land)
        for name, wv in (("W_all", w), ("W_land", w * is_land)):
            grid.sums[name] = grid.sums.get(name, 0) + np.bincount(gidx, np.bincount(inv, wv, len(uniq)), grid.n)
        for name, arr in fields.items():
            v = pix(arr).astype(np.float64)
            ok = is_land & np.isfinite(v)
            wsum = np.bincount(inv[ok], weights=w[ok], minlength=len(uniq))
            vsum = np.bincount(inv[ok], weights=w[ok] * v[ok], minlength=len(uniq))
            grid.sums[f"W_{name}"] = grid.sums.get(f"W_{name}", 0) + np.bincount(gidx, wsum, grid.n)
            grid.sums[f"S_{name}"] = grid.sums.get(f"S_{name}", 0) + np.bincount(gidx, vsum, grid.n)


def _mean(grid: EarthGrid, name: str) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return grid.sums[f"S_{name}"] / grid.sums[f"W_{name}"]


# --------------------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------------------

MIN_CELL_FRAC = 0.25      # como build_earth_mask.py: la celda está en la máscara si ≥ 25 % de su tierra lo está


def build_earth_grid(res: int = 6) -> tuple[pd.DataFrame, str]:
    t0 = time.time()
    log(f"Malla H3 res {res} de la Tierra…")
    grid = EarthGrid(res)
    log(f"  {grid.n:,} celdas")

    m = load_mask()
    land, cls = m["land"], m["cls"]
    relief_source = process_relief(grid, land)
    topo = finish_topography(grid).drop(columns=["mola_measured_frac"])

    log("Campos de 0,05° (temperatura, lluvia, polvo, sílice, nieve) …")
    fields = compute_fields(m, relief=False)                      # el relieve ya va por su cuenta (arriba)
    fields["kept"] = (cls > 0).astype("f4")
    for k in (1, 2, 3):
        fields[f"env{k}"] = (cls == k).astype("f4")
    log("Agregando a celdas (3×3 subpíxeles por píxel) …")
    accumulate_cmg(grid, fields, land)

    with np.errstate(invalid="ignore", divide="ignore"):
        land_frac = grid.sums["W_land"] / grid.sums["W_all"]
    cols = {name: _mean(grid, name) for name in fields if not name.startswith("env") and name != "kept"}
    kept = _mean(grid, "kept")
    env = np.vstack([_mean(grid, f"env{k}") for k in (1, 2, 3)])
    env_cls = np.where(np.nan_to_num(kept) > 0, np.nanargmax(np.nan_to_num(env, nan=-1), axis=0) + 1, 0).astype("f4")
    env_cls[~(land_frac > 0)] = np.nan

    df = pd.concat([
        pd.DataFrame({"h3": [h3i.int_to_str(int(c)) for c in grid.cells], "lat": grid.lat, "lon": grid.lon}),
        pd.DataFrame({"land_frac": land_frac,
                      "in_mask": np.where(land_frac > 0, (np.nan_to_num(kept) >= MIN_CELL_FRAC).astype("f4"), np.nan),
                      "env": env_cls, "kept_frac": kept}),
        topo, pd.DataFrame(cols),
        pd.DataFrame({"sun_elev_max_deg": np.where(land_frac > 0,
                                                   90.0 - np.clip(np.abs(grid.lat) - EARTH_OBLIQUITY_DEG, 0, None), np.nan)}),
    ], axis=1)
    df.loc[~(land_frac > 0), [c for c in df.columns if c not in ("h3", "lat", "lon", "land_frac")]] = np.nan
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / f"earth_h3r{res}.parquet"
    df = df.astype({c: "float32" for c in df.columns if c not in ("h3", "lat", "lon")})
    df.to_parquet(out, index=False)
    log(f"Hecho en {(time.time() - t0) / 60:.1f} min → {out} ({out.stat().st_size / 1e6:.0f} MB)")
    return df, relief_source


# name → (dtype, scale, offset, unit, label). Las variables COMPARTIDAS con Marte usan su misma codificación.
EARTH_WEB_COLUMNS: dict[str, tuple[str, float, float, str, str]] = {
    "slope_deg":        ("u1", 0.25, 0.0, "°", "Slope (median, ~460 m baseline)"),
    "roughness_deg":    ("u1", 0.25, 0.0, "°", "Roughness (RMS slope after removing a plane)"),
    "t_mean_K":         ("u1", 1.0, 100.0, "K", "Mean surface temperature (12 monthly means of (day + night) / 2)"),
    "t_max_K":          ("u1", 1.0, 100.0, "K", "Max surface temperature (warmest month, 13:30)"),
    "t_min_K":          ("u1", 1.0, 100.0, "K", "Min surface temperature (coldest month, 01:30)"),
    "t_night_K":        ("u1", 1.0, 100.0, "K", "Night surface temperature (annual mean, 01:30)"),
    "dust_aod":         ("u1", 0.01, 0.0, "", "Dust optical depth (550 nm, annual mean)"),
    "sun_elev_max_deg": ("u1", 0.5, 0.0, "°", "Highest noon Sun elevation over a year"),
    "elevation_m":      ("u2", 1.0, -10000.0, "m", "Elevation above sea level"),
    "precip_mm_year":   ("u1", 20.0, 0.0, "mm/yr", "Mean annual precipitation"),
    "silica_wt_pct":    ("u1", 0.5, 0.0, "wt%", "Silica (SiO2) of exposed rock and soil (53N–53S)"),
    "snow_cover_pct":   ("u1", 0.5, 0.0, "%", "Mean annual snow cover"),
    "land_frac":        ("u1", 0.005, 0.0, "", "Fraction of the cell that is land"),
    "in_mask":          ("u1", 1.0, 0.0, "", "1 = analog search zone (desert, polar ice, arid open land)"),
    "env":              ("u1", 1.0, 0.0, "", "0 outside · 1 polar ice · 2 desert (bare) · 3 arid open"),
}


def earth_sources(relief_source: str) -> dict[str, str]:
    lst = "MODIS Aqua MYD11C3 v061, climatology 2019–2023 (NASA LP DAAC)"
    return {
        "slope_deg": relief_source, "roughness_deg": relief_source, "elevation_m": relief_source,
        "t_mean_K": lst, "t_max_K": lst, "t_min_K": lst, "t_night_K": lst,
        "dust_aod": "NASA MERRA-2 M2TMNXAER DUEXTTAU, climatology 2019–2023 (GES DISC)",
        "sun_elev_max_deg": "computed from latitude and obliquity (23.44°)",
        "precip_mm_year": "GPM IMERG Final monthly v07, 2019–2023 (GES DISC)",
        "silica_wt_pct": "ECOSTRESS ECO_L3G_WPS v001 (NASA LP DAAC)",
        "snow_cover_pct": "MODIS Terra MOD10CM v061, climatology 2019–2023 (NSIDC)",
        "land_frac": "MODIS MCD12C1 v061 2025 (NASA LP DAAC)",
        "in_mask": "MCD12C1 + IMERG (scripts/build_earth_mask.py)",
        "env": "MCD12C1 + IMERG (scripts/build_earth_mask.py)",
    }
