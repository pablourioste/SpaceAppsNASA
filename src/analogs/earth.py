"""Tierra: de los productos descargados a FICHAS (una fila por píxel de 0,05° y por hexágono H3 res 5).

    scripts/build_earth_mask.py        # 1) máscara (MCD12C1 + IMERG)  → interim/earth_mask_005deg.npz
    scripts/build_earth_features.py    # 2) este módulo                → processed/fichas_tierra_*.parquet

Todo se calcula en la malla común de MODIS (0,05°, ~5,6 km, "CMG"); cada producto se lee una vez.
La tabla por hexágono es la media ponderada por área (cos lat) de esos píxeles.
Carpetas de entrada y qué es cada una: src/analogs/catalog.py.

Tiempo:
  - FIJO        relieve (SRTMGL30 + ETOPO 2022), sílice (ECOSTRESS 2023–24), cubierta del suelo (2025)
  - CLIMA       2019–2023 → condiciones TÍPICAS, no récords:
                    t_mean_K = media de los 12 meses de (día + noche)/2   (solo noche si no hay día: noche polar)
                    t_max_K  = mes más cálido de la temperatura de día (13:30)
                    t_min_K  = mes más frío de la temperatura de noche (01:30; el mínimo real, al alba, es algo menor)
                    precip_mm_year, dust_aod (media anual) / dust_aod_max (mes con más polvo), snow_cover_pct
Escala del relieve: 30″ (~0,93 km) → pendiente a esa línea base (misma que MOLA 64 px/°).
  slope_deg     = pendiente media del píxel/hexágono
  roughness_deg = RMS de la pendiente (mismo criterio que mars.py)
"""
from __future__ import annotations

import re
import warnings
import zipfile
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from .paths import INTERIM, PROCESSED, RAW

EARTH_RADIUS_M = 6_371_008.8
EARTH_OBLIQUITY_DEG = 23.44
RES = 0.05
N_LAT, N_LON = 3600, 7200
LAT = 90 - RES / 2 - RES * np.arange(N_LAT)       # centros de fila, de norte a sur
LON = -180 + RES / 2 + RES * np.arange(N_LON)
H3_RES = 5

RAW_EARTH = RAW / "earth"
MASK_NPZ = INTERIM / "earth_mask_005deg.npz"
CELLS_NPZ = INTERIM / f"earth_cmg_h3r{H3_RES}.npz"


# --------------------------------------------------------------------------------------
# Malla común y correspondencia píxel → hexágono
# --------------------------------------------------------------------------------------

def load_mask() -> dict[str, np.ndarray]:
    if not MASK_NPZ.exists():
        raise FileNotFoundError(f"Falta {MASK_NPZ}. Ejecuta antes: python scripts/build_earth_mask.py")
    with np.load(MASK_NPZ) as z:
        return {k: z[k] for k in z.files}


def pixel_cells(land: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(fila, columna, hexágono como entero) de cada píxel de tierra. Se calcula una vez y se guarda."""
    if CELLS_NPZ.exists():
        with np.load(CELLS_NPZ) as z:
            if len(z["i"]) == int(land.sum()):
                return z["i"], z["j"], z["cell"]
    i, j = np.nonzero(land)
    print(f"  H3 res {H3_RES} para {len(i):,} píxeles (una sola vez)…")
    cell = np.fromiter((h3.str_to_int(h3.latlng_to_cell(a, b, H3_RES)) for a, b in zip(LAT[i], LON[j])),
                       dtype=np.int64, count=len(i))
    INTERIM.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CELLS_NPZ, i=i, j=j, cell=cell)
    return i, j, cell


def to_hexagons(i: np.ndarray, j: np.ndarray, cell: np.ndarray, fields: dict[str, np.ndarray]) -> pd.DataFrame:
    """Media ponderada por área (cos lat) de cada campo 0,05° dentro de cada hexágono, ignorando NaN."""
    w = np.cos(np.radians(LAT[i]))
    df = pd.DataFrame({"cell": cell})
    for name, grid in fields.items():
        v = grid[i, j].astype("f8")
        ok = np.isfinite(v)
        df[name + "__s"] = np.where(ok, v * w, 0.0)
        df[name + "__w"] = np.where(ok, w, 0.0)
    g = df.groupby("cell").sum()
    out = pd.DataFrame(index=g.index)
    for name in fields:
        out[name] = (g[name + "__s"] / g[name + "__w"]).where(g[name + "__w"] > 0)
    return out


# --------------------------------------------------------------------------------------
# Temperatura: MYD11C3 (Aqua), climatología mensual
# --------------------------------------------------------------------------------------

def lst_climatology(land: np.ndarray) -> dict[str, np.ndarray]:
    """t_mean_K, t_max_K, t_min_K y n_months en la malla 0,05° (NaN fuera de tierra o sin dato)."""
    from pyhdf.SD import SD, SDC

    files = sorted((RAW_EARTH / "myd11c3").glob("MYD11C3.A*.hdf"))
    if not files:
        print("  [temperatura] no hay ficheros MYD11C3 → se deja vacía")
        return {}
    i, j = np.nonzero(land)
    n = len(i)
    sums = {k: np.zeros((12, n), "f8") for k in ("day", "night")}
    cnts = {k: np.zeros((12, n), "u2") for k in ("day", "night")}
    years = set()
    for f in files:
        m = re.search(r"\.A(\d{4})(\d{3})\.", f.name)
        year, doy = int(m.group(1)), int(m.group(2))
        years.add(year)
        month = (pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)).month - 1
        sd = SD(str(f), SDC.READ)
        for key, sds in (("day", "LST_Day_CMG"), ("night", "LST_Night_CMG")):
            raw = sd.select(sds).get()[i, j]
            ok = raw > 0                                # 0 = sin dato
            sums[key][month, ok] += raw[ok] * 0.02      # factor de escala → K
            cnts[key][month, ok] += 1
        sd.end()
    print(f"  [temperatura] MYD11C3: {len(files)} meses, años {min(years)}–{max(years)}")
    with np.errstate(invalid="ignore", divide="ignore"):
        day = np.where(cnts["day"] > 0, sums["day"] / cnts["day"], np.nan)        # (12, n) climatología
        night = np.where(cnts["night"] > 0, sums["night"] / cnts["night"], np.nan)
        both = np.where(np.isfinite(day) & np.isfinite(night), (day + night) / 2, np.where(np.isfinite(night), night, day))
        months_ok = np.isfinite(both).sum(0)
        warnings.simplefilter("ignore", RuntimeWarning)    # píxeles sin ningún mes: media de vacío
        res = {
            "t_mean_K": np.where(months_ok >= 6, np.nanmean(both, 0), np.nan),
            "t_max_K": np.nanmax(np.where(np.isfinite(day), day, -np.inf), 0),
            "t_min_K": np.nanmin(np.where(np.isfinite(night), night, np.inf), 0),
            "lst_months": months_ok.astype("f4"),
        }
    res["t_max_K"][~np.isfinite(res["t_max_K"])] = np.nan
    res["t_min_K"][~np.isfinite(res["t_min_K"])] = np.nan
    out = {}
    for k, v in res.items():
        g = np.full((N_LAT, N_LON), np.nan, "f4")
        g[i, j] = v
        out[k] = g
    return out


# --------------------------------------------------------------------------------------
# Relieve: SRTMGL30 → pendiente a ~0,93 km, agregada a 0,05° (bloques de 6×6 píxeles)
# --------------------------------------------------------------------------------------

def _read_srtm30_tile(zpath: Path) -> tuple[np.ndarray, dict]:
    """Pieza SRTMGL30 (formato GTOPO30): el zip solo trae el .DEM, sin cabecera.
    El nombre da la esquina superior izquierda (W020N40 = 20°O, 40°N); 30″ por píxel,
    4800 columnas (40°) × 6000 filas (50°), entero de 16 bits big-endian, 0 = mar."""
    m = re.match(r"([EW])(\d{3})([NS])(\d{2})", zpath.name.upper())
    west = int(m.group(2)) * (1 if m.group(1) == "E" else -1)
    north = int(m.group(4)) * (1 if m.group(3) == "N" else -1)
    with zipfile.ZipFile(zpath) as z:
        dem_name = next(n for n in z.namelist() if n.lower().endswith(".dem"))
        z16 = np.frombuffer(z.read(dem_name), dtype=">i2")
    cols = 4800
    z16 = z16.reshape(-1, cols)
    dem = z16.astype("f4")
    dem[(z16 == -9999) | (z16 == 0)] = np.nan     # el mar viene como 0 (comprobado); 0 m exactos en tierra: casi nunca
    dim = 1 / 120
    return dem, {"ulx": west + dim / 2, "uly": north - dim / 2, "dim": dim}


def srtm_relief() -> dict[str, np.ndarray]:
    """elevation_m, slope_deg (media) y slope_sq (media de pendiente², para la RMS) en la malla 0,05°."""
    tiles = sorted((RAW_EARTH / "srtmgl30").glob("*.zip"))
    if not tiles:
        print("  [relieve] no hay ficheros SRTMGL30 → se deja vacío")
        return {}
    out = {k: np.full((N_LAT, N_LON), np.nan, "f4") for k in ("elevation_m", "slope_deg", "slope_sq")}
    for t in tiles:
        dem, g = _read_srtm30_tile(t)
        rows, cols = dem.shape
        top = g["uly"] + g["dim"] / 2                       # borde superior (ULYMAP es el centro del píxel)
        lat = top - g["dim"] * (np.arange(rows) + 0.5)
        dy = np.radians(g["dim"]) * EARTH_RADIUS_M          # metros por píxel norte–sur
        dx = dy * np.clip(np.cos(np.radians(lat)), 1e-3, None)[:, None]
        dzdy = np.gradient(dem, dy, axis=0)
        dzdx = np.gradient(dem, axis=1) / dx
        slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        k = int(round(RES / g["dim"]))                      # 6 píxeles de 30″ por píxel de 0,05°
        r0 = int(round((90 - top) / RES))
        c0 = int(round((g["ulx"] - g["dim"] / 2 + 180) / RES))
        br, bc = rows // k, cols // k
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # bloques de mar: media de todo NaN
            for name, field in (("elevation_m", dem), ("slope_deg", slope), ("slope_sq", slope ** 2)):
                blk = field[: br * k, : bc * k].reshape(br, k, bc, k)
                out[name][r0:r0 + br, c0:c0 + bc] = np.nanmean(blk, axis=(1, 3))
    n = int(np.isfinite(out["elevation_m"]).sum())
    print(f"  [relieve] SRTMGL30: {len(tiles)} piezas → {n:,} píxeles de 0,05° con dato")
    return out


def _slope_deg(dem: np.ndarray, lat_rows: np.ndarray, dim_deg: float) -> np.ndarray:
    dy = np.radians(dim_deg) * EARTH_RADIUS_M
    dx = dy * np.clip(np.cos(np.radians(lat_rows)), 1e-3, None)[:, None]
    return np.degrees(np.arctan(np.hypot(np.gradient(dem, axis=1) / dx, np.gradient(dem, dy, axis=0))))


def etopo_fill(relief: dict[str, np.ndarray], land: np.ndarray) -> dict[str, np.ndarray]:
    """Rellena con ETOPO 2022 (30″, global) los píxeles de tierra SIN SRTMGL30: Ártico (>60° N) y
    Antártida/subantártico (<56° S). Misma resolución (30″) y mismo cálculo de pendiente.
    ETOPO incluye el fondo del mar: en esas latitudes solo se usa lo que está por encima de 0 m."""
    tif = next((RAW_EARTH / "etopo2022_30s").glob("*.tif"), None)
    if tif is None:
        print("  [relieve] no hay ETOPO 2022 → el Ártico y la Antártida se quedan sin pendiente")
        return relief
    import rasterio
    from rasterio.windows import Window

    try:
        with rasterio.open(tif) as src:
            src.read(1, window=Window(0, src.height - 1, src.width, 1))   # ¿fichero completo? (lee la última fila)
    except Exception as e:  # noqa: BLE001 — descarga a medias o fichero dañado
        print(f"  [relieve] ETOPO 2022 incompleto o ilegible ({type(e).__name__}) → se salta; relanza download_earth.py dem")
        return relief
    if not relief:
        relief = {k: np.full((N_LAT, N_LON), np.nan, "f4") for k in ("elevation_m", "slope_deg", "slope_sq")}
    need = land & ~np.isfinite(relief["elevation_m"])           # tierra sin dato de SRTMGL30
    rows_needed = np.nonzero(need.any(axis=1))[0]
    if not len(rows_needed):
        return relief
    filled = 0
    with rasterio.open(tif) as src:
        dim = src.transform.a                                    # 30″ = 1/120°
        k = int(round(RES / dim))                                # 6 píxeles de 30″ por píxel de 0,05°
        width = N_LON * k
        strip = 200                                              # filas de 0,05° por bloque (10°)
        for r0 in range(0, N_LAT, strip):
            r1 = min(r0 + strip, N_LAT)
            if not need[r0:r1].any():
                continue
            top, bottom = r0 * k, r1 * k                         # filas de 30″ (se ignora el medio píxel de registro)
            h0, h1 = max(top - 1, 0), min(bottom + 1, src.height)
            z = src.read(1, window=Window(0, h0, width, h1 - h0)).astype("f4")
            z[z <= 0] = np.nan                                   # mar y plataformas: fuera
            lat_rows = 90 - dim * (np.arange(h0, h1) + 0.5)
            slope = _slope_deg(z, lat_rows, dim)
            sl = slice(top - h0, top - h0 + (bottom - top))
            with np.errstate(invalid="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                for name, field in (("elevation_m", z[sl]), ("slope_deg", slope[sl]), ("slope_sq", slope[sl] ** 2)):
                    blk = np.nanmean(field.reshape(r1 - r0, k, N_LON, k), axis=(1, 3))
                    tgt = relief[name][r0:r1]
                    m = need[r0:r1]
                    tgt[m] = blk[m]
            filled += int((need[r0:r1] & np.isfinite(relief["elevation_m"][r0:r1])).sum())
    print(f"  [relieve] ETOPO 2022: {filled:,} píxeles de 0,05° rellenados (polos)")
    return relief


# --------------------------------------------------------------------------------------
# Polvo (MERRA-2), sílice (ECOSTRESS), nieve (MOD10CM)
# --------------------------------------------------------------------------------------

def merra2_dust() -> dict[str, np.ndarray]:
    """dust_aod (media anual del polvo, 550 nm), dust_aod_max (mes de más polvo), total_aod.
    Climatología 2019–2023; se pasa a 0,05° con el vecino más cercano (la malla MERRA-2 es de ~55 km)."""
    import h5py

    files = sorted((RAW_EARTH / "merra2_dust").glob("*.nc4"))
    if not files:
        print("  [polvo] no hay ficheros MERRA-2 → se deja vacío")
        return {}
    sums = {v: np.zeros((12, 361, 576)) for v in ("DUEXTTAU", "TOTEXTTAU")}
    n = np.zeros(12)
    for f in files:
        month = int(re.search(r"\.(\d{4})(\d{2})", f.name).group(2)) - 1
        with h5py.File(f, "r") as h:
            for v in sums:
                a = h[v][0].astype("f8")
                a[a > 1e10] = np.nan                             # _FillValue 1e15
                sums[v][month] += a
        n[month] += 1
    clim = {v: s / n[:, None, None] for v, s in sums.items()}
    li = np.clip(np.rint((LAT + 90) / 0.5).astype(int), 0, 360)
    lj = np.rint((LON + 180) / 0.625).astype(int) % 576
    out = {
        "dust_aod": clim["DUEXTTAU"].mean(0)[li[:, None], lj[None, :]].astype("f4"),
        "dust_aod_max": clim["DUEXTTAU"].max(0)[li[:, None], lj[None, :]].astype("f4"),
        "total_aod": clim["TOTEXTTAU"].mean(0)[li[:, None], lj[None, :]].astype("f4"),
    }
    print(f"  [polvo] MERRA-2: {len(files)} meses")
    return out


def ecostress_silica() -> dict[str, np.ndarray]:
    """silica_wt_pct: % en peso de SiO₂, media de los píxeles de 0,01° dentro de cada 0,05° (53° N – 53° S)."""
    tif = next((RAW_EARTH / "ecostress_wps").glob("*.tif"), None)
    if tif is None:
        print("  [sílice] no hay ECOSTRESS → se deja vacío")
        return {}
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    dst = np.full((N_LAT, N_LON), np.nan, "f4")
    with rasterio.open(tif) as src:
        reproject(source=rasterio.band(src, 1), destination=dst, src_nodata=src.nodata, dst_nodata=np.nan,
                  dst_transform=from_origin(-180, 90, RES, RES), dst_crs="EPSG:4326",
                  resampling=Resampling.average)
    dst[(dst <= 0) | (dst > 100)] = np.nan
    print(f"  [sílice] ECOSTRESS: {int(np.isfinite(dst).sum()):,} píxeles de 0,05° con dato")
    return {"silica_wt_pct": dst}


def snow_climatology(land: np.ndarray) -> dict[str, np.ndarray]:
    """snow_cover_pct (media anual de la climatología mensual) y snow_months (meses con > 50 % de nieve)."""
    from pyhdf.SD import SD, SDC

    files = sorted((RAW_EARTH / "mod10cm").glob("MOD10CM.A*.hdf"))
    if not files:
        print("  [nieve] no hay ficheros MOD10CM → se deja vacía")
        return {}
    i, j = np.nonzero(land)
    sums = np.zeros((12, len(i)), "f4")
    cnts = np.zeros((12, len(i)), "u2")
    for f in files:
        m = re.search(r"\.A(\d{4})(\d{3})\.", f.name)
        month = (pd.Timestamp(year=int(m.group(1)), month=1, day=1) + pd.Timedelta(days=int(m.group(2)) - 1)).month - 1
        sd = SD(str(f), SDC.READ)
        v = sd.select("Snow_Cover_Monthly_CMG").get()[i, j]
        sd.end()
        ok = v <= 100                                           # > 100: noche, nube, agua, sin dato
        sums[month, ok] += v[ok]
        cnts[month, ok] += 1
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        clim = np.where(cnts > 0, sums / cnts, np.nan)
        pct = np.nanmean(clim, 0)
        months = (clim >= 50).sum(0).astype("f4")
    out = {}
    for name, v in (("snow_cover_pct", pct), ("snow_months", months)):
        g = np.full((N_LAT, N_LON), np.nan, "f4")
        g[i, j] = v
        out[name] = g
    print(f"  [nieve] MOD10CM: {len(files)} meses")
    return out


# --------------------------------------------------------------------------------------
# Ficha por hexágono
# --------------------------------------------------------------------------------------

def sun_elevation_max(lat_deg: np.ndarray, obliquity_deg: float = EARTH_OBLIQUITY_DEG) -> np.ndarray:
    """Altura máxima del Sol a mediodía a lo largo del año (horizonte plano)."""
    return 90.0 - np.maximum(0.0, np.abs(lat_deg) - obliquity_deg)


ENV_NAMES = {0: "fuera", 1: "hielo polar", 2: "desierto (suelo desnudo)", 3: "árido abierto (matorral/estepa)"}


def compute_fields(m: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Todas las variables en la malla 0,05° (se leen los productos una sola vez)."""
    fields: dict[str, np.ndarray] = {"precip_mm_year": m["precip_mm_year"]}
    fields.update(etopo_fill(srtm_relief(), m["land"]))
    fields.update(lst_climatology(m["land"]))
    fields.update(merra2_dust())
    fields.update(ecostress_silica())
    fields.update(snow_climatology(m["land"]))
    return fields


def build_earth_pixels(fields: dict[str, np.ndarray], m: dict[str, np.ndarray]) -> pd.DataFrame:
    """Ficha por PÍXEL de 0,05° (~5,6 km en el ecuador, menos hacia los polos): la malla nativa de MODIS.
    Es la resolución más fina a la que existen TODAS las variables a la vez."""
    i, j = np.nonzero(m["land"])
    cls = m["cls"][i, j]
    out = pd.DataFrame({
        "pixel": (i.astype(np.int64) * N_LON + j).astype(np.int32),     # fila·7200 + columna
        "lat": LAT[i].astype("f4"), "lon": LON[j].astype("f4"),
        "in_mask": cls > 0, "env": cls.astype("i1"),
    })
    out["env_name"] = pd.Categorical(out["env"].map(ENV_NAMES))
    for name, grid in fields.items():
        if name != "slope_sq":
            out[name] = grid[i, j].astype("f4")
    if "slope_sq" in fields:
        out["roughness_deg"] = np.sqrt(fields["slope_sq"][i, j]).astype("f4")
    out["sun_elev_max_deg"] = sun_elevation_max(out["lat"].to_numpy()).astype("f4")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / "fichas_tierra_005deg.parquet", index=False)
    return out


def build_earth_cells(fields: dict[str, np.ndarray] | None = None, m: dict[str, np.ndarray] | None = None) -> pd.DataFrame:
    m = m or load_mask()
    land = m["land"]
    i, j, cell = pixel_cells(land)
    fields = fields or compute_fields(m)
    print("  Agregando a hexágonos…")
    hexes = to_hexagons(i, j, cell, fields)
    if "slope_sq" in hexes:
        hexes["roughness_deg"] = np.sqrt(hexes.pop("slope_sq"))

    mask = pd.read_parquet(PROCESSED / "earth_mask_h3r5.parquet")
    mask["cell_int"] = [h3.str_to_int(c) for c in mask["cell"]]
    mask = mask.drop(columns=[c for c in hexes.columns if c in mask.columns])
    out = mask.set_index("cell_int").join(hexes, how="left").reset_index(drop=True)
    out["sun_elev_max_deg"] = sun_elevation_max(out["lat"].to_numpy())
    first = ["cell", "lat", "lon", "in_mask", "kept_frac", "env", "env_name"]
    out = out[first + [c for c in out.columns if c not in first]]
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / f"fichas_tierra_h3r{H3_RES}.parquet", index=False)
    return out
