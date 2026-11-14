"""Task 3.5: the Mars card grid — every variable on H3 resolution-5 hexagons (decision 007).

    python scripts/build_mars_grid.py

One row per H3 res-5 cell (~2 M cells, ~9 km) with every Mars variable, written to
data/processed/mars_h3r5.parquet, plus the cards of the Mars target sites in
data/processed/fichas_objetivos_mars.parquet.

Method (ROADMAP 3.5, decided 2026-11-14): fine pixels → ~9 km cells is a LOW-PASS (area-weighted
average); a HIGH-PASS (plane removed) is used only for roughness. Every average is area-weighted.

Latitude is planetocentric, longitude −180…180 east; H3 is used on the Mars sphere with those
coordinates (H3 only needs lat/lon; distances below use the Mars radius).
"""
from __future__ import annotations

import time
from pathlib import Path

import h3.api.basic_int as h3i
import numpy as np
import pandas as pd

from .mars import (DUST_IR_TO_VIS, MARS_OBLIQUITY_DEG, MARS_RADIUS_M, bin_tes_atmosphere,
                   read_grs_table)
from .paths import CATALOGS, INTERIM, PROCESSED, RAW

H3_RES = 5
RAW_MARS = RAW / "mars"
POLAR_LAT = 88.0          # the 128 ppd tiles stop at ±88°: beyond it, the polar maps are used
NO_ICE_DEPTH_M = 10.0     # [assumption] value stored when SWIM finds no ice in the top ~5 m+
# SWIM consistency near 0 means "inconclusive", not "ice": with a threshold of 0 about 43 % of the
# "ice" cells fell at |lat| < 30°; with 0.25 only 1.6 % (checked 2026-11-14). Arcadia (known
# shallow ice) has 0.51.
SWIM_ICE_THRESHOLD = 0.25


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def wrap180(lon):
    return (np.asarray(lon) + 180.0) % 360.0 - 180.0


# --------------------------------------------------------------------------------------
# The grid and the accumulator
# --------------------------------------------------------------------------------------

def all_cells() -> np.ndarray:
    """Every H3 cell at H3_RES, sorted (uint64)."""
    cells = np.fromiter((c for r in h3i.get_res0_cells() for c in h3i.cell_to_children(r, H3_RES)),
                        dtype=np.uint64)
    cells.sort()
    return cells


class Grid:
    """All cells + their centres + weighted sums that can be merged across tiles and chunks."""

    def __init__(self) -> None:
        self.cells = all_cells()
        centres = np.array([h3i.cell_to_latlng(int(c)) for c in self.cells])
        self.lat, self.lon = centres[:, 0], centres[:, 1]
        self.n = len(self.cells)
        self.sums: dict[str, np.ndarray] = {}
        self.median_parts: dict[str, list[pd.DataFrame]] = {}

    def index(self, ids: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.cells, ids)

    def add(self, name: str, gidx: np.ndarray, values: np.ndarray) -> None:
        s = np.bincount(gidx, weights=values, minlength=self.n)
        self.sums[name] = self.sums.get(name, 0) + s

    def add_median(self, name: str, gidx: np.ndarray, med: np.ndarray, weight: np.ndarray) -> None:
        self.median_parts.setdefault(name, []).append(pd.DataFrame({"i": gidx, "m": med, "w": weight}))

    def median(self, name: str) -> np.ndarray:
        """Weighted median per cell. A cell split between chunks/tiles gets the weight-averaged
        median of its parts (approximation, only for the few cells on chunk borders)."""
        out = np.full(self.n, np.nan)
        if name not in self.median_parts:
            return out
        df = pd.concat(self.median_parts[name], ignore_index=True)
        df["mw"] = df["m"] * df["w"]
        g = df.groupby("i")[["mw", "w"]].sum()
        out[g.index.to_numpy()] = (g["mw"] / g["w"]).to_numpy()
        return out


def _block_centres(v: np.ndarray, s: int) -> np.ndarray:
    k = -(-len(v) // s)
    return np.pad(v, (0, k * s - len(v)), mode="edge").reshape(k, s).mean(axis=1)


def assign_cells(lat_rows: np.ndarray, lon_cols: np.ndarray, stride: int = 1) -> np.ndarray:
    """H3 cell of every pixel of a separable lat/lon grid.

    With stride > 1 the cell is computed once per stride×stride block (at its centre) and
    repeated: used for MOLA, whose pixels are ~20× smaller than a cell (border error ≤ 1 pixel).
    """
    la = _block_centres(lat_rows, stride)
    lo = wrap180(_block_centres(lon_cols, stride)).tolist()
    ids = np.empty((len(la), len(lo)), dtype=np.uint64)
    for i, a in enumerate(la.tolist()):
        ids[i] = [h3i.latlng_to_cell(a, b, H3_RES) for b in lo]
    if stride > 1:
        ids = np.repeat(np.repeat(ids, stride, axis=0), stride, axis=1)
    return ids[: len(lat_rows), : len(lon_cols)]


def weighted_median_groups(inv: np.ndarray, values: np.ndarray, w: np.ndarray, n_groups: int):
    """Weighted median of `values` for each group id in `inv` (0..n_groups-1)."""
    order = np.lexsort((values, inv))
    g, v, ww = inv[order], values[order], w[order]
    starts = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
    sizes = np.diff(np.r_[starts, len(g)])
    gid = np.repeat(np.arange(len(starts)), sizes)
    cw = np.cumsum(ww)
    before = cw[starts] - ww[starts]
    total = np.add.reduceat(ww, starts)
    within = cw - before[gid]
    pos = np.where(within >= total[gid] / 2, np.arange(len(g)), len(g))
    first = np.minimum.reduceat(pos, starts)
    med = np.full(n_groups, np.nan)
    med[g[starts]] = v[np.minimum(first, len(g) - 1)]
    return med


# --------------------------------------------------------------------------------------
# MOLA: slope, roughness (high-pass), measured fraction, elevation
# --------------------------------------------------------------------------------------

def _accumulate_topography(grid: Grid, ids, z, gx, gy, lat, lon, w, measured, elevation_ok=True,
                           xy=None):
    """Add one block of topography pixels to the grid sums (all arrays flattened, same length).

    The plane for the roughness high-pass is fitted in the same axes as the gradient (gx, gy):
    east/north metres around each cell centre by default, or the given `xy` (polar map axes).
    """
    uniq, inv = np.unique(ids, return_inverse=True)
    gidx = grid.index(uniq)
    if xy is None:
        clat, clon = grid.lat[gidx][inv], grid.lon[gidx][inv]
        x = MARS_RADIUS_M * np.cos(np.deg2rad(clat)) * np.deg2rad(wrap180(lon - clon))
        y = MARS_RADIUS_M * np.deg2rad(lat - clat)
    else:
        x, y = xy
    gi = gidx[inv]
    for name, val in [("W", w), ("Sx", w * x), ("Sy", w * y), ("Sz", w * z), ("Sxx", w * x * x),
                      ("Syy", w * y * y), ("Sxy", w * x * y), ("Sxz", w * x * z), ("Syz", w * y * z),
                      ("Sgx", w * gx), ("Sgy", w * gy), ("Sgg", w * (gx * gx + gy * gy)),
                      ("Wmeas", w * measured)]:
        grid.add(name, gi, val)
    if elevation_ok:
        grid.add("Welev", gi, w)
        grid.add("Selev", gi, w * z)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    med = weighted_median_groups(inv, slope, w, len(uniq))
    wsum = np.bincount(inv, weights=w, minlength=len(uniq))
    grid.add_median("slope", gidx, med, wsum)


def process_mola_tile(grid: Grid, stem: str, chunk: int = 352, stride: int = 2) -> None:
    """One 128 ppd MEGDR tile (44°×90°), processed in row chunks with a 1-row halo."""
    from .mars import _label_values

    d = RAW_MARS / "mola_megdr_128ppd"
    lab = _label_values(d / f"megt{stem}hb.lbl")
    lines, samples = int(lab["LINES"]), int(lab["LINE_SAMPLES"])
    ppd = float(lab["MAP_RESOLUTION"].split()[0])
    max_lat = float(lab["MAXIMUM_LATITUDE"].split()[0])
    west = float(lab["WESTERNMOST_LONGITUDE"].split()[0])
    topo = np.memmap(d / f"megt{stem}hb.img", dtype=">i2", mode="r", shape=(lines, samples))
    counts = np.memmap(d / f"megc{stem}hb.img", dtype=">u1", mode="r", shape=(lines, samples))
    lat_rows = max_lat - (np.arange(lines) + 0.5) / ppd
    lon_cols = west + (np.arange(samples) + 0.5) / ppd
    step = np.deg2rad(1 / ppd) * MARS_RADIUS_M

    for r0 in range(0, lines, chunk):
        r1 = min(lines, r0 + chunk)
        h0, h1 = max(0, r0 - 1), min(lines, r1 + 1)
        z = topo[h0:h1].astype(np.float64)
        lat_h = lat_rows[h0:h1]
        gy = -np.gradient(z, axis=0) / step                              # d z / d north
        gx = np.gradient(z, axis=1) / (step * np.cos(np.deg2rad(lat_h)))[:, None]   # d z / d east
        cut = slice(r0 - h0, r0 - h0 + (r1 - r0))
        z, gx, gy = z[cut], gx[cut], gy[cut]
        lat = np.repeat(lat_rows[r0:r1], samples)
        lon = np.tile(lon_cols, r1 - r0)
        ids = assign_cells(lat_rows[r0:r1], lon_cols, stride).ravel()
        # cells centred beyond ±88° are handled by the polar maps (no double counting)
        keep = np.abs(grid.lat[grid.index(ids)]) <= POLAR_LAT
        w = np.cos(np.deg2rad(lat))
        meas = (np.asarray(counts[r0:r1]).ravel() > 0).astype(np.float64)
        _accumulate_topography(grid, ids[keep], z.ravel()[keep], gx.ravel()[keep], gy.ravel()[keep],
                               lat[keep], lon[keep], w[keep], meas[keep])


POLAR_R_KM, POLAR_SCALE_KM = 3376.2, 0.460357861
ORIENTATIONS = [(1, 0.0), (-1, 0.0), (1, 180.0), (-1, 180.0)]   # lon = sign·angle + offset


def polar_xy_km(rows, cols, n: int = 10240):
    """Map coordinates (km) of polar MEGDR pixels, pole at the image centre, +y up."""
    x = (np.asarray(cols) - n / 2 + 0.5) * POLAR_SCALE_KM
    y = (n / 2 - 0.5 - np.asarray(rows)) * POLAR_SCALE_KM
    return x, y


def polar_latlon(rows, cols, north: bool, n: int = 10240, orientation: int = 0):
    """Lat/lon of polar-stereographic MEGDR pixels (sphere R = 3376.2 km, 0.460357861 km/px).
    `orientation` picks where longitude 0° points and which way longitude grows; it is chosen by
    comparing with the 128 ppd tiles in the overlap (check_polar_orientation)."""
    x, y = polar_xy_km(rows, cols, n)
    colat = 2 * np.degrees(np.arctan(np.hypot(x, y) / (2 * POLAR_R_KM)))
    lat = 90 - colat if north else colat - 90
    ang = np.degrees(np.arctan2(x, -y))          # 0° pointing down the image
    sign, offset = ORIENTATIONS[orientation]
    return lat, wrap180(sign * ang + offset)


def read_polar(north: bool):
    from .mars import _label_values

    d = RAW_MARS / "mola_megdr_polar128"
    stem = "n" if north else "s"
    lab = _label_values(d / f"megt_{stem}_128_1.lbl")
    n = int(lab["LINES"])
    topo = np.memmap(d / f"megt_{stem}_128_1.img", dtype=">u2", mode="r", shape=(n, n))
    counts = np.memmap(d / f"megc_{stem}_128.img", dtype=">u1", mode="r", shape=(n, n))
    return topo, counts, n


def check_polar_orientation(north: bool) -> int:
    """Pick the orientation whose polar elevations match the 128 ppd tiles at ~85° latitude."""
    from .download import mola128_tile
    from .mars import read_pds3_image

    from .mars import _label_values

    topo, _, n = read_polar(north)
    lat0 = 85.0 if north else -85.0
    lons = np.arange(-170, 180, 20.0)
    tile_vals = []
    for lo in lons:                       # read single pixels straight from the tiles (memmap)
        t = mola128_tile(lat0, lo)
        img = RAW_MARS / "mola_megdr_128ppd" / f"megt{t}hb.img"
        lab = _label_values(img.with_suffix(".lbl"))
        lines, samples = int(lab["LINES"]), int(lab["LINE_SAMPLES"])
        ppd = float(lab["MAP_RESOLUTION"].split()[0])
        r = int((float(lab["MAXIMUM_LATITUDE"].split()[0]) - lat0) * ppd)
        c = int(((lo - float(lab["WESTERNMOST_LONGITUDE"].split()[0])) % 360) * ppd)
        tile_vals.append(float(np.memmap(img, dtype=">i2", mode="r", shape=(lines, samples))[r, c]))
    tile_vals = np.array(tile_vals)
    rows, cols = np.meshgrid(np.arange(0, n, 8), np.arange(0, n, 8), indexing="ij")
    rows, cols = rows.ravel(), cols.ravel()
    best, best_err = 0, np.inf
    for o in range(len(ORIENTATIONS)):
        lat, lon = polar_latlon(rows, cols, north, n, o)
        vals = []
        for lo in lons:
            k = np.argmin((lat - lat0) ** 2 + (wrap180(lon - lo) * np.cos(np.deg2rad(lat0))) ** 2)
            vals.append(topo[rows[k], cols[k]] * 0.25 - 8000)
        # polar heights are relative to a 3,396,000 m sphere, tiles to the areoid: compare shapes
        err = np.nanstd(np.array(vals) - tile_vals)
        if err < best_err:
            best, best_err = o, err
    log(f"  polar {'N' if north else 'S'}: orientation {best} (std of difference vs tiles {best_err:.0f} m)")
    return best


def process_polar(grid: Grid, north: bool, orientation: int) -> None:
    """Cells centred beyond ±88°, from the polar stereographic map (pixels ~460 m, map axes)."""
    topo, counts, n = read_polar(north)
    half = 300                                   # ±300 px ≈ ±138 km around the pole (> 2°)
    sl = slice(n // 2 - half, n // 2 + half)
    z = topo[sl, sl].astype(np.float64) * 0.25 - 8000
    step = 460.357861
    gy = -np.gradient(z, axis=0) / step           # map axes; the magnitude is what matters
    gx = np.gradient(z, axis=1) / step
    rr, cc = np.meshgrid(np.arange(n // 2 - half, n // 2 + half), np.arange(n // 2 - half, n // 2 + half),
                         indexing="ij")
    lat, lon = polar_latlon(rr.ravel(), cc.ravel(), north, n, orientation)
    ids = np.array([h3i.latlng_to_cell(a, b, H3_RES) for a, b in zip(lat.tolist(), lon.tolist())],
                   dtype=np.uint64)
    keep = np.abs(grid.lat[grid.index(ids)]) > POLAR_LAT
    meas = (np.asarray(counts[sl, sl]).ravel() > 0).astype(np.float64)
    w = np.ones(keep.sum())                      # equal-area enough this close to the pole
    # the gradient is in map axes, so the roughness plane is fitted in map axes too (metres)
    x_km, y_km = polar_xy_km(rr.ravel(), cc.ravel(), n)
    _accumulate_topography(grid, ids[keep], z.ravel()[keep], gx.ravel()[keep], gy.ravel()[keep],
                           lat[keep], lon[keep], w, meas[keep], elevation_ok=False,
                           xy=(x_km[keep] * 1000, y_km[keep] * 1000))


def finish_topography(grid: Grid) -> pd.DataFrame:
    s = grid.sums
    W = s["W"]
    with np.errstate(invalid="ignore", divide="ignore"):
        # plane z = a + b x + c y fitted per cell (weighted least squares)
        A = np.stack([np.stack([W, s["Sx"], s["Sy"]], -1),
                      np.stack([s["Sx"], s["Sxx"], s["Sxy"]], -1),
                      np.stack([s["Sy"], s["Sxy"], s["Syy"]], -1)], -2)
        rhs = np.stack([s["Sz"], s["Sxz"], s["Syz"]], -1)
        ok = W > 0
        coef = np.full((grid.n, 3), np.nan)
        det = np.linalg.det(A[ok])
        good = np.abs(det) > 1e-6
        idx = np.flatnonzero(ok)[good]
        coef[idx] = np.linalg.solve(A[idx], rhs[idx][..., None])[..., 0]
        b, c = coef[:, 1], coef[:, 2]
        ms = s["Sgg"] / W - 2 * (b * s["Sgx"] + c * s["Sgy"]) / W + b * b + c * c
        roughness = np.degrees(np.arctan(np.sqrt(np.clip(ms, 0, None))))
        out = pd.DataFrame({
            "slope_deg": grid.median("slope"),
            "roughness_deg": roughness,
            "mola_measured_frac": s["Wmeas"] / W,
            "elevation_m": s["Selev"] / s["Welev"],
        })
    out.loc[~ok, :] = np.nan
    return out


# --------------------------------------------------------------------------------------
# ~3 km rasters (TES thermal inertia, SWIM): area-of-intersection weights by sub-pixels
# --------------------------------------------------------------------------------------

def accumulate_fine_raster(grid: Grid, lat_rows, lon_cols, layers: dict[str, np.ndarray],
                           sub: int = 3, chunk: int = 40) -> None:
    """Area-weighted mean per cell of several co-registered rasters (NaN = no data).

    Each pixel is split into sub×sub sub-pixels, each assigned to its cell by its centre: the
    weight a pixel gets in a cell ≈ the area of the pixel inside the cell.
    """
    dlat = abs(lat_rows[1] - lat_rows[0])
    dlon = abs(lon_cols[1] - lon_cols[0])
    offs = (np.arange(sub) + 0.5) / sub - 0.5
    sub_lon = (lon_cols[:, None] + offs[None, :] * dlon).ravel()
    for r0 in range(0, len(lat_rows), chunk):
        r1 = min(len(lat_rows), r0 + chunk)
        sub_lat = (lat_rows[r0:r1, None] - offs[None, :] * dlat).ravel()
        ids = assign_cells(sub_lat, sub_lon, 1)
        uniq, inv = np.unique(ids.ravel(), return_inverse=True)
        gidx = grid.index(uniq)
        w = np.repeat(np.cos(np.deg2rad(sub_lat)), len(sub_lon))
        for name, arr in layers.items():
            v = np.repeat(np.repeat(arr[r0:r1], sub, axis=0), sub, axis=1).ravel()
            ok = np.isfinite(v)
            wsum = np.bincount(inv[ok], weights=w[ok], minlength=len(uniq))
            vsum = np.bincount(inv[ok], weights=w[ok] * v[ok], minlength=len(uniq))
            grid.sums[f"W_{name}"] = grid.sums.get(f"W_{name}", 0) + np.bincount(gidx, wsum, grid.n)
            grid.sums[f"S_{name}"] = grid.sums.get(f"S_{name}", 0) + np.bincount(gidx, vsum, grid.n)


def mean_of(grid: Grid, name: str) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return grid.sums[f"S_{name}"] / grid.sums[f"W_{name}"]


def process_tes_ti(grid: Grid) -> pd.DataFrame:
    from .mars import read_pds3_image

    d = RAW_MARS / "tes_thermal_inertia"
    layers, georef = {}, None
    for when in ("day", "night"):
        ti = read_pds3_image(d / f"global_ti_{when}_2007.img", nodata=0)
        msk = read_pds3_image(d / f"global_ti_msk_{when}_2007.img")
        layers[f"ti_{when}_meas"] = np.where(msk.values == 1, ti.values, np.nan)
        layers[f"ti_{when}_all"] = ti.values
        georef = ti
    lat_rows = georef.max_lat - (np.arange(georef.values.shape[0]) + 0.5) / georef.ppd
    lon_cols = georef.west_lon + (np.arange(georef.values.shape[1]) + 0.5) / georef.ppd
    accumulate_fine_raster(grid, lat_rows, lon_cols, layers)
    out = {}
    for when in ("day", "night"):
        meas, allv = mean_of(grid, f"ti_{when}_meas"), mean_of(grid, f"ti_{when}_all")
        out[f"thermal_inertia_{when}_SI"] = np.where(np.isfinite(meas), meas, allv)
    return pd.DataFrame(out)


def process_swim(grid: Grid) -> pd.DataFrame:
    import rasterio

    d = RAW_MARS / "swim2_ice"
    layers, lat_rows, lon_cols = {}, None, None
    for name, f in [("ci_0_1m", "SWIM2_c0_1.tif"), ("ci_1_5m", "SWIM2_c1_5.tif"), ("ci_5m", "SWIM2_c_5.tif")]:
        with rasterio.open(d / f) as src:
            a = src.read(1).astype(np.float64)
            a[a == src.nodata] = np.nan
            layers[name] = a
            t = src.transform
            R = 3396190.0  # Mars2000 sphere of the GeoTIFF CRS (equidistant cylindrical, clon 0)
            cols = t.c + (np.arange(src.width) + 0.5) * t.a
            rows = t.f + (np.arange(src.height) + 0.5) * t.e
            lon_cols = np.degrees(cols / R)
            lat_rows = np.degrees(rows / R)
    accumulate_fine_raster(grid, lat_rows, lon_cols, layers)
    ci = {k: mean_of(grid, k) for k in layers}
    return pd.DataFrame({"swim_ci_0_1m": ci["ci_0_1m"], "swim_ci_1_5m": ci["ci_1_5m"],
                         "swim_ci_5m": ci["ci_5m"],
                         "ice_depth_m": ice_depth_from_swim(ci["ci_0_1m"], ci["ci_1_5m"], ci["ci_5m"])})


# Beyond SWIM (|lat| > 60°): epithermal neutrons see hydrogen in the top ~1 m.
# Threshold calibrated in the 45–60° band against SWIM "ice within 1 m" (balanced accuracy 0.80,
# checked 2026-11-14). The 2002 NS map was taken in northern WINTER: seasonal CO2 frost hides the
# hydrogen north of ~70°N (median flux 6.5 cps there vs 1.6 cps at the south pole), so north of
# NEUTRON_NORTH_LIMIT the depth is an ASSUMPTION from ground-ice stability (Phoenix found ice at
# ~5 cm at 68°N). The source of every value is kept in `ice_depth_source`.
# MGS never flew over |lat| > ~87.1° (orbit inclination 92.9°): almost no MOLA shots there and
# the polar maps are interpolated → slope ~0 is an artefact. Slope/roughness are dropped beyond it.
MOLA_COVERAGE_LAT = 87.0


def apply_polar_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Blank slope/roughness beyond MOLA's coverage; fix the NS neutron row at ±89.75° (stored as 0,
    a fill value) with the nearest valid row (±89.25°)."""
    out = df.copy()
    beyond = out["lat"].abs() > MOLA_COVERAGE_LAT
    out.loc[beyond, ["slope_deg", "roughness_deg", "mola_measured_frac"]] = np.nan
    return out


NEUTRON_ICE_CPS = 6.1
NEUTRON_NORTH_LIMIT = 70.0
ICE_SOURCE = {1: "SWIM 2.0", 2: "neutrons (GRS NS, calibrated on SWIM)",
              3: "assumed: ground-ice stability (no reliable data north of 70°N)"}


def fill_ice_beyond_swim(df: pd.DataFrame) -> pd.DataFrame:
    """Add `ice_depth_source` (1 SWIM, 2 neutrons, 3 assumption) and fill ice_depth_m beyond SWIM.

    Neutrons can only say "ice within ~1 m" (0.5 m) or "not detected in the top ~1 m" (NaN with
    source 2): they do not see deeper.
    """
    depth = df["ice_depth_m"].to_numpy(dtype=float).copy()
    source = np.where(np.isfinite(depth), 1.0, np.nan)
    flux = df["ns_epithermal_cps"].to_numpy(dtype=float)
    lat = df["lat"].to_numpy(dtype=float)
    beyond = ~np.isfinite(depth)
    by_neutrons = beyond & np.isfinite(flux) & (lat < NEUTRON_NORTH_LIMIT)
    depth[by_neutrons & (flux <= NEUTRON_ICE_CPS)] = 0.5
    source[by_neutrons] = 2
    assumed = beyond & (lat >= NEUTRON_NORTH_LIMIT)
    depth[assumed] = 0.5
    source[assumed] = 3
    out = df.copy()
    out["ice_depth_m"] = depth.astype("float32")
    out["ice_depth_source"] = source.astype("float32")
    return out


def ice_depth_from_swim(c01, c15, c5, thr: float = SWIM_ICE_THRESHOLD) -> np.ndarray:
    """Depth class (m) from the three SWIM consistency maps: shallowest layer above `thr`."""
    c01, c15, c5 = (np.asarray(a, dtype=float) for a in (c01, c15, c5))
    depth = np.full(c01.shape, np.nan)
    covered = np.isfinite(c01) | np.isfinite(c15) | np.isfinite(c5)
    depth[covered] = NO_ICE_DEPTH_M
    depth[covered & (np.nan_to_num(c5, nan=-1) > thr)] = 5.0
    depth[covered & (np.nan_to_num(c15, nan=-1) > thr)] = 3.0
    depth[covered & (np.nan_to_num(c01, nan=-1) > thr)] = 0.5
    return depth


# --------------------------------------------------------------------------------------
# Coarse products: value of the coarse cell that contains the hexagon centre
# --------------------------------------------------------------------------------------

def _regular_lookup(lat, lon, table: pd.DataFrame, deg: float) -> np.ndarray:
    """Look up a table on a regular lat/lon grid of `deg` cells (columns lat, lon, value)."""
    nr, nc = int(round(180 / deg)), int(round(360 / deg))
    grid = np.full((nr, nc), np.nan)
    r = np.floor((table["lat"].to_numpy() + 90) / deg).astype(int).clip(0, nr - 1)
    c = np.floor((wrap180(table["lon"].to_numpy()) + 180) / deg).astype(int).clip(0, nc - 1)
    grid[r, c] = table["value"].to_numpy()
    rr = np.floor((lat + 90) / deg).astype(int).clip(0, nr - 1)
    cc = np.floor((wrap180(lon) + 180) / deg).astype(int).clip(0, nc - 1)
    return grid[rr, cc]


def process_grs(grid: Grid) -> pd.DataFrame:
    from .mars import _grs_unit

    out = {}
    for el in ["h2o", "cl", "fe", "si", "k", "th"]:
        tab = RAW_MARS / "grs_elements" / f"{el}_sr_5x5.tab"
        unit = _grs_unit(tab.with_suffix(".lbl"))
        suffix = "ppm" if ("PPM" in unit.upper() or "MILLION" in unit.upper()) else "wt_pct"
        out[f"grs_{el}_{suffix}"] = _regular_lookup(grid.lat, grid.lon, read_grs_table(tab, 0, 1, 2), 5.0)
    out["ns_epithermal_cps"] = neutron_lookup(grid.lat, grid.lon)
    return pd.DataFrame(out)


def neutron_lookup(lat, lon) -> np.ndarray:
    """Epithermal neutron flux at each point. The rows at ±89.25° and ±89.75° are stored as 0
    (fill value, not a measurement; checked 2026-11-14): they are treated as no data and filled
    from the last measured row, ±88.75°."""
    ns = read_grs_table(RAW_MARS / "grs_special" / "ns_epithermal_020917.tab", 1, 0, 2)
    ns.loc[ns["value"] <= 0, "value"] = np.nan
    lat = np.asarray(lat, dtype=float)
    v = _regular_lookup(lat, lon, ns, 0.5)
    pole = ~np.isfinite(v) & (np.abs(lat) > 89.0)
    v[pole] = _regular_lookup(np.sign(lat[pole]) * 88.75, np.asarray(lon)[pole], ns, 0.5)
    return v


def mcs_night_day(cell_deg: float = 5.0) -> pd.DataFrame:
    files = sorted((RAW_MARS / "mcs_tsurf_my31").glob("*_tsurf.csv"))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = df[df["T_surf"] > 0].copy()
    hour = df["LTST"] * 24                    # LTST is a fraction of a sol
    df["kind"] = np.where(hour.between(10, 18), "day", np.where((hour < 6) | (hour >= 20), "night", "other"))
    df["lat_bin"] = np.floor((df["Surf_lat"] + 90) / cell_deg).astype(int)
    df["lon_bin"] = np.floor((wrap180(df["Surf_lon"]) + 180) / cell_deg).astype(int)
    t = df[df["kind"] != "other"].pivot_table(index=["lat_bin", "lon_bin"], columns="kind",
                                               values="T_surf", aggfunc="mean")
    return t.rename(columns={"day": "mcs_t_day_K", "night": "mcs_t_night_K"}).reset_index()


def process_atmosphere(grid: Grid, cell_deg: float = 5.0) -> pd.DataFrame:
    cache = INTERIM / "mars_tes_atmos_5deg.parquet"
    if cache.exists():
        tes = pd.read_parquet(cache)
    else:
        tes = bin_tes_atmosphere(RAW_MARS / "tes_atmos_my26", cell_deg=cell_deg)
        INTERIM.mkdir(parents=True, exist_ok=True)
        tes.to_parquet(cache, index=False)
    mcs = mcs_night_day(cell_deg)
    nr, nc = int(180 / cell_deg), int(360 / cell_deg)
    rr = np.floor((grid.lat + 90) / cell_deg).astype(int).clip(0, nr - 1)
    cc = np.floor((wrap180(grid.lon) + 180) / cell_deg).astype(int).clip(0, nc - 1)

    def to_grid(df, col):
        a = np.full((nr, nc), np.nan)
        a[df["lat_bin"].to_numpy(), df["lon_bin"].to_numpy()] = df[col].to_numpy()
        return a[rr, cc]

    t_day_tes = to_grid(tes, "t_day_K_mean")
    t_day_mcs = to_grid(mcs, "mcs_t_day_K") if "mcs_t_day_K" in mcs else np.full(grid.n, np.nan)
    t_night = to_grid(mcs, "mcs_t_night_K") if "mcs_t_night_K" in mcs else np.full(grid.n, np.nan)
    t_day = np.where(np.isfinite(t_day_tes), t_day_tes, t_day_mcs)
    return pd.DataFrame({
        "t_day_K": t_day,
        "t_night_K": t_night,
        "t_mean_K": (t_day + t_night) / 2,
        "t_max_K": to_grid(tes, "t_day_K_p95"),
        "dust_od_9um": to_grid(tes, "dust_od_9um_mean"),
        "dust_aod": to_grid(tes, "dust_od_9um_mean") * DUST_IR_TO_VIS,
        "ice_od_12um": to_grid(tes, "ice_od_12um_mean"),
        "p_surf_Pa": to_grid(tes, "p_surf_Pa_mean"),
    })


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def build_mars_grid(tiles: list[str] | None = None, with_poles: bool = True) -> pd.DataFrame:
    from .download import MOLA128_ALL_TILES

    t0 = time.time()
    log("Building the H3 res-5 grid of Mars…")
    grid = Grid()
    log(f"  {grid.n:,} cells")

    for i, stem in enumerate(tiles or MOLA128_ALL_TILES, 1):
        log(f"MOLA tile {stem} ({i}/{len(tiles or MOLA128_ALL_TILES)})")
        process_mola_tile(grid, stem)
    if with_poles:
        for north in (True, False):
            o = check_polar_orientation(north)
            log(f"MOLA polar {'north' if north else 'south'}")
            process_polar(grid, north, o)
    topo = finish_topography(grid)

    log("TES thermal inertia (area-weighted, 3×3 sub-pixels)")
    ti = process_tes_ti(grid)
    log("SWIM ice consistency (area-weighted, 3×3 sub-pixels)")
    swim = process_swim(grid)
    log("GRS (coarse lookup)")
    grs = process_grs(grid)
    log("TES + MCS atmosphere (5° lookup)")
    atm = process_atmosphere(grid)

    lat = grid.lat
    df = pd.concat([
        pd.DataFrame({"h3": [h3i.int_to_str(int(c)) for c in grid.cells], "lat": lat, "lon": grid.lon}),
        topo, ti, swim, grs, atm,
        pd.DataFrame({"sun_elev_max_deg": 90.0 - np.clip(np.abs(lat) - MARS_OBLIQUITY_DEG, 0, None)}),
    ], axis=1)
    df = fill_ice_beyond_swim(apply_polar_limits(df))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "mars_h3r5.parquet"
    df.astype({c: "float32" for c in df.columns if c not in ("h3", "lat", "lon")}).to_parquet(out, index=False)
    log(f"Done in {(time.time() - t0) / 60:.1f} min → {out} ({out.stat().st_size / 1e6:.0f} MB)")
    return df


def build_mars_targets(grid_df: pd.DataFrame) -> pd.DataFrame:
    """Card of each Mars target site = card of the H3 res-5 cell (~9 km) that contains it."""
    import re

    sites = pd.read_csv(CATALOGS / "target_sites.csv")
    sites = sites[sites["body"] == "mars"].dropna(subset=["lat", "lon"]).reset_index(drop=True)
    by_h3 = grid_df.set_index("h3")
    rows = []
    for s in sites.itertuples():
        cell = h3i.int_to_str(h3i.latlng_to_cell(float(s.lat), float(s.lon), H3_RES))
        card = by_h3.loc[cell].drop(["lat", "lon"]).to_dict()
        rows.append({"id": re.sub(r"[^a-z0-9]+", "_", s.name.lower()).strip("_"), "name": s.name,
                     "body": "mars", "lat": float(s.lat), "lon": float(s.lon), "type": s.type,
                     "h3": cell, **card})
    out = pd.DataFrame(rows)
    out.to_parquet(PROCESSED / "fichas_objetivos_mars.parquet", index=False)
    return out
