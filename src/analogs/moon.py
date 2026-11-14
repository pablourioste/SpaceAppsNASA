"""Moon: card grid for the WHOLE Moon on H3 hexagons + the cards of the Moon target sites.

    python scripts/build_moon_grid.py

ROADMAP task 3.7. Same idea as the Mars grid (src/analogs/mars.py, task 3.5): every hexagon gets
one value per variable, computed from the pixels that fall INSIDE the hexagon; clicking anywhere
in the hexagon returns those values.

Grid: H3 resolution 4 (H3_RES). On the Moon a res-4 hexagon is ~131.7 km² (~12.3 km across),
the H3 level closest to the Mars res-5 hexagons (~71.6 km², ~9.1 km). Res 5 would give only
~4.7 km on the Moon (H3 cells are defined by angle, and the Moon is small). 288,122 cells.

Inputs (data/raw/moon/, see scripts/download_moon.py and docs/06_datos_luna.md):
    lola_ldem64/          LOLA global DEM, 64 px/deg (~474 m)        → slope, roughness
    lola_ldec128/         LOLA shots per cell, 128 px/deg            → % of measured cells (QC)
    diviner_gcp/          Diviner temperature per 0.5° tile and local time → T mean/max/min
    diviner_prp/          Diviner polar resource product (south, ~0.5 km)  → ice depth, polar T
    pgda_south_pole/      PGDA permanent-shadow mask, 80–90° S (20 m)     → PSR fraction
    lunar_prospector_grs/ Lunar Prospector GRS, 2° equal-area cells       → FeO, TiO2, Al2O3…, K, Th, U
    diviner_rocks/        Diviner rock abundance, 32 px/deg, ±60°         → rock abundance
    lroc_pits/            LROC pit atlas (278 pits)                       → caves

Method, the same as the Mars table in ROADMAP 3.5 (decision 006: same scale on every body):
    - fine rasters → hexagon: area-weighted statistics of the pixels inside the hexagon (low-pass);
    - high-pass ONLY for roughness: remove the hexagon's mean gradient (≈ best-fit plane) and take
      the RMS of the residual slope;
    - coarse products (Diviner GCP 0.5°, Lunar Prospector 2°): area-weighted mean of the coarse
      cells whose centre falls in the hexagon, or the coarse cell that contains the hexagon centre.
Conventions: planetocentric latitude, longitude −180…180 east, SI units. Missing or "not
applicable" = NaN, never 0 and never sentinel codes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .paths import CATALOGS, PROCESSED, RAW

MOON_RADIUS_M = 1_737_400.0
MOON_OBLIQUITY_DEG = 1.54
H3_RES = 4
RAW_MOON = RAW / "moon"

SLOPE_BIN_DEG = 0.25           # slope histogram per hexagon → weighted median (±0.125°)
SLOPE_NBINS = 160              # 0–40° (last bin collects anything steeper)
POLE_SKIP_DEG = 89.88          # beyond this, longitude differences stop being local (see _relief)

# Units, sources and method of every output column (also written next to the grid as a CSV)
NO_ICE_DEPTH_M = 10.0          # same convention as Mars (mars_grid.NO_ICE_DEPTH_M): "no ice found"
SUN_FORMULA_MAX_LAT = 80.0     # docs/07: at the lunar poles relief decides the light → no flat formula

COLUMNS = {
    "elevation_m": ("m", "LOLA ldem_64", "area-weighted mean height above the 1,737.4 km sphere"),
    "slope_deg":("deg", "LOLA ldem_64 (~474 m)", "central differences, baseline ~950 m in both directions; area-weighted median in the hexagon"),
    "roughness_deg": ("deg", "LOLA ldem_64", "high-pass: slope of (gradient − hexagon mean gradient); area-weighted RMS"),
    "lola_measured_frac": ("0-1", "LOLA ldec_128", "area-weighted fraction of 474 m pixels with ≥1 LOLA shot (QC)"),
    "t_mean_K": ("K", "Diviner GCP (0.5°)", "(mean of day bins 6–18 h + mean of night bins) / 2 of tbol per tile; area-weighted over tiles"),
    "t_max_K": ("K", "Diviner GCP", "max of tbol over local time per tile; area-weighted mean over tiles"),
    "t_min_K": ("K", "Diviner GCP", "min of tbol over local time per tile; area-weighted mean over tiles"),
    "t_n_valid": ("count", "Diviner GCP", "mean number of local-time bins (of 96) with data (QC)"),
    "ice_frac_1m": ("0-1", "Diviner PRP (lat ≤ −80°)", "fraction of the hexagon where water ice is stable within 1 m; |lat| < 60°: 0 [physical assumption]"),
    "ice_frac_surface": ("0-1", "Diviner PRP (lat ≤ −80°)", "fraction where ice is stable AT the surface (ice_depth = 0)"),
    "ice_depth_m": ("m", "Diviner PRP (lat ≤ −80°)", "median ice-stability depth (0 = at the surface); 10 = no stable ice within the product range (2.87 m) or away from the poles; NaN = no data (60–80° and the north pole)"),
    "ice_depth_source": ("code", "—", "1 = Diviner PRP model · 3 = assumed (|lat| < 60°: ice not stable near the surface)"),
    "prp_t_avg_2cm_K": ("K", "Diviner PRP (lat ≤ −80°)", "median annual mean temperature at 2 cm depth (polar detail, extra)"),
    "prp_t_max_K": ("K", "Diviner PRP (lat ≤ −80°)", "median annual max surface temperature (polar detail, extra)"),
    "psr_frac": ("0-1", "PGDA LPSR_80S_20MPP (lat ≤ −80.4°)", "fraction of the hexagon in permanent shadow"),
    "feo_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "W_FEO × 100 of the 2° cell containing the hexagon centre [units: verify]"),
    "tio2_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "ídem TIO2"),
    "al2o3_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "ídem W_AL2O3"),
    "mgo_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "ídem W_MGO"),
    "cao_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "ídem W_CAO"),
    "silica_wt_pct": ("wt%", "Lunar Prospector GRS 2°", "W_SIO2 × 100 (name as in configs/variables.yaml)"),
    "k_ppm": ("ppm", "Lunar Prospector GRS 2°", "W_K [units: verify]"),
    "th_ppm": ("ppm", "Lunar Prospector GRS 2°", "W_TH [units: verify]"),
    "u_ppm": ("ppm", "Lunar Prospector GRS 2°", "W_U [units: verify]"),
    "rock_abundance_pct": ("%", "Diviner rock abundance (±60°, ~948 m)", "area-weighted mean × 100; NaN beyond ±60°"),
    "pit_count": ("count", "LROC pit atlas", "pits inside the hexagon"),
    "pit_dist_km": ("km", "LROC pit atlas", "great-circle distance from the hexagon centre to the nearest pit"),
    "caves": ("0/1", "LROC pit atlas", "1 if there is at least one pit in the hexagon"),
    "sun_elev_max_deg": ("deg", "geometry", "90 − max(0, |lat| − 1.54°) at the hexagon centre (flat horizon); NaN for |lat| ≥ 80°: there relief decides the light (docs/07) → use psr_frac"),
    "precip_mm_year": ("mm/year", "—", "0: it never rains on the Moon (as in configs/variables.yaml)"),
    "dust_aod": ("-", "—", "not applicable on the Moon (no atmosphere): always NaN"),
}


# --------------------------------------------------------------------------------------
# H3 helpers
# --------------------------------------------------------------------------------------

def latlon_to_cells(lat: np.ndarray, lon: np.ndarray, res: int = H3_RES) -> np.ndarray:
    """H3 cell (uint64) of every point. Uses h3ronpy (vectorised, ~3× faster) if installed."""
    lat = np.asarray(lat, dtype=np.float64).ravel()
    lon = ((np.asarray(lon, dtype=np.float64).ravel() + 180.0) % 360.0) - 180.0
    try:
        from h3ronpy.vector import coordinates_to_cells
        return np.asarray(coordinates_to_cells(lat, lon, res), dtype=np.uint64)
    except ImportError:
        import h3
        return np.fromiter((h3.str_to_int(h3.latlng_to_cell(a, b, res)) for a, b in zip(lat, lon)),
                           dtype=np.uint64, count=lat.size)


class Grid:
    """Every H3 cell of the body at `res`, with a dense index 0…N−1 for fast accumulation."""

    def __init__(self, res: int = H3_RES):
        import h3
        cells = sorted(h3.str_to_int(c) for b in h3.get_res0_cells() for c in h3.cell_to_children(b, res))
        self.res = res
        self.ids = np.array(cells, dtype=np.uint64)
        centres = [h3.cell_to_latlng(h3.int_to_str(c)) for c in cells]
        self.lat = np.array([c[0] for c in centres])
        self.lon = np.array([c[1] for c in centres])

    def __len__(self) -> int:
        return self.ids.size

    def index(self, cells: np.ndarray) -> np.ndarray:
        idx = np.searchsorted(self.ids, cells)
        idx[idx >= self.ids.size] = 0
        assert (self.ids[idx] == cells).all(), "point outside the grid"
        return idx

    def sum(self, idx: np.ndarray, weights: np.ndarray) -> np.ndarray:
        return np.bincount(idx, weights=weights, minlength=len(self))


def _area_weight(lat_deg: np.ndarray) -> np.ndarray:
    """Relative area of a pixel of a simple-cylindrical grid (∝ cos latitude)."""
    return np.cos(np.radians(lat_deg))


# --------------------------------------------------------------------------------------
# Relief: slope, roughness, measured fraction (LOLA)
# --------------------------------------------------------------------------------------

def _relief(grid: Grid, rows_per_chunk: int = 256) -> pd.DataFrame:
    """Slope (weighted median) and roughness (high-pass RMS) from LOLA ldem_64.

    Slope at every pixel by central differences with the SAME baseline in both directions
    (~950 m): north–south ±1 row; east–west ±k columns with k = round(1/cos lat), so that the
    east–west step stays ~474 m even near the poles. Rows closer than 0.12° to a pole are
    skipped (there ±k columns span too much longitude to be a local difference).
    """
    ppd, nl, ns = 64, 11520, 23040
    dem = np.memmap(RAW_MOON / "lola_ldem64" / "ldem_64.img", dtype="<i2", mode="r", shape=(nl, ns))
    ldec_path = RAW_MOON / "lola_ldec128" / "ldec_128.img"
    cnt = np.memmap(ldec_path, dtype="<i2", mode="r", shape=(2 * nl, 2 * ns)) if ldec_path.exists() else None

    dy = math.radians(1 / ppd) * MOON_RADIUS_M                 # 474 m per row
    lon_px = (np.arange(ns) + 0.5) / ppd
    n = len(grid)
    W, Gx, Gy, G2, Wm, Zs = (np.zeros(n) for _ in range(6))
    hist = np.zeros((n, SLOPE_NBINS), dtype=np.float32)

    for r0 in range(1, nl - 1, rows_per_chunk):
        r1 = min(r0 + rows_per_chunk, nl - 1)
        rows = np.arange(r0, r1)
        lat = 90.0 - (rows + 0.5) / ppd
        keep = np.abs(lat) <= POLE_SKIP_DEG
        if not keep.any():
            continue
        rows, lat = rows[keep], lat[keep]
        z = dem[rows[0] - 1: rows[-1] + 2].astype(np.float32) * 0.5     # m, with a 1-row halo
        coslat = np.cos(np.radians(lat))
        gy = (z[:-2] - z[2:]) / (2 * dy)                                  # north positive
        gx = np.empty_like(gy)
        for i, c in enumerate(coslat):
            k = max(1, int(round(1 / c)))
            row = z[i + 1]
            gx[i] = (np.roll(row, -k) - np.roll(row, k)) / (2 * k * dy * c)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))

        LAT = np.repeat(lat, ns)
        LON = np.tile(lon_px, lat.size)
        idx = grid.index(latlon_to_cells(LAT, LON))
        w = np.repeat(_area_weight(lat), ns)
        gxr, gyr = gx.ravel(), gy.ravel()
        W += grid.sum(idx, w)
        Gx += grid.sum(idx, w * gxr)
        Gy += grid.sum(idx, w * gyr)
        G2 += grid.sum(idx, w * (gxr ** 2 + gyr ** 2))
        Zs += grid.sum(idx, w * z[1:-1].ravel())
        if cnt is not None:
            c = cnt[2 * rows[0]: 2 * (rows[-1] + 1)].reshape(rows.size, 2, ns, 2)
            measured = (c > 0).any(axis=(1, 3)).ravel()
            Wm += grid.sum(idx, w * measured)

        # slope histogram per hexagon, only for the cells touched by this chunk
        b = np.minimum((slope.ravel() / SLOPE_BIN_DEG).astype(np.int64), SLOPE_NBINS - 1)
        uniq, inv = np.unique(idx, return_inverse=True)
        local = np.bincount(inv * SLOPE_NBINS + b, weights=w, minlength=uniq.size * SLOPE_NBINS)
        hist[uniq] += local.reshape(uniq.size, SLOPE_NBINS).astype(np.float32)

    with np.errstate(invalid="ignore", divide="ignore"):
        mx, my = Gx / W, Gy / W
        var = np.maximum(G2 / W - mx ** 2 - my ** 2, 0.0)
        rough = np.degrees(np.arctan(np.sqrt(var)))
        measured_frac = Wm / W if cnt is not None else np.full(n, np.nan)
        elevation = Zs / W
    return pd.DataFrame({"elevation_m": elevation, "slope_deg": _hist_median(hist), "roughness_deg": rough,
                         "lola_measured_frac": measured_frac})


def _hist_median(hist: np.ndarray) -> np.ndarray:
    """Weighted median from per-row histograms (linear interpolation inside the bin)."""
    total = hist.sum(axis=1)
    cum = np.cumsum(hist, axis=1)
    half = total / 2
    j = (cum < half[:, None]).sum(axis=1).clip(0, hist.shape[1] - 1)
    rows = np.arange(hist.shape[0])
    before = np.where(j > 0, cum[rows, j - 1], 0.0)
    inbin = hist[rows, j]
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(inbin > 0, (half - before) / inbin, 0.5)
    med = (j + frac) * SLOPE_BIN_DEG
    med[total <= 0] = np.nan
    return med


# --------------------------------------------------------------------------------------
# Temperature: Diviner GCP (whole Moon) and PRP (south pole)
# --------------------------------------------------------------------------------------

def gcp_tiles() -> pd.DataFrame:
    """One row per 0.5° tile: T mean/max/min over the diurnal cycle (tbol)."""
    parts = []
    for f in sorted((RAW_MOON / "diviner_gcp").glob("global_cumul_avg_cyl_*_002.tab")):
        df = pd.read_csv(f, usecols=[0, 1, 2, 10], names=["clon", "clat", "ltim", "tbol"], header=0)
        df.loc[df["tbol"] < 0, "tbol"] = np.nan                       # −9999 = no data
        df["day"] = df["ltim"].between(6, 18)
        g = df.groupby(["clon", "clat"], sort=False)["tbol"]
        tiles = pd.DataFrame({"t_n_valid": g.count(), "t_max_K": g.max(), "t_min_K": g.min()})
        tiles["t_day"] = df[df["day"]].groupby(["clon", "clat"])["tbol"].mean()
        tiles["t_night"] = df[~df["day"]].groupby(["clon", "clat"])["tbol"].mean()
        parts.append(tiles.reset_index())
    tiles = pd.concat(parts, ignore_index=True)
    tiles["t_mean_K"] = (tiles["t_day"] + tiles["t_night"]) / 2        # NaN if day or night is missing
    return tiles.drop(columns=["t_day", "t_night"])


def _coarse_to_grid(grid: Grid, lat: np.ndarray, lon: np.ndarray, values: pd.DataFrame,
                    lookup) -> pd.DataFrame:
    """Coarse cells → hexagons: area-weighted mean of the coarse cells whose centre falls in the
    hexagon; hexagons with no centre inside take the coarse cell that contains their own centre."""
    idx = grid.index(latlon_to_cells(lat, lon))
    w = _area_weight(lat)
    out = {}
    W = grid.sum(idx, w)
    for col in values.columns:
        v = values[col].to_numpy(dtype=float)
        ok = np.isfinite(v)
        num, den = grid.sum(idx[ok], (w * v)[ok]), grid.sum(idx[ok], w[ok])
        with np.errstate(invalid="ignore", divide="ignore"):
            out[col] = np.where(den > 0, num / den, np.nan)
    res = pd.DataFrame(out)
    empty = W == 0
    if empty.any():
        fill = lookup(grid.lat[empty], grid.lon[empty])
        for col in values.columns:
            res.loc[empty, col] = fill[col].to_numpy()
    return res


def _temperature(grid: Grid) -> pd.DataFrame:
    tiles = gcp_tiles()
    key = tiles.set_index(["clon", "clat"])

    def lookup(lat, lon):
        clon = np.floor(((lon + 180) % 360 - 180) / 0.5) * 0.5 + 0.25
        clat = np.clip(np.floor(lat / 0.5) * 0.5 + 0.25, -89.75, 89.75)
        return key.reindex(pd.MultiIndex.from_arrays([np.round(clon, 2), np.round(clat, 2)]))

    cols = ["t_mean_K", "t_max_K", "t_min_K", "t_n_valid"]
    return _coarse_to_grid(grid, tiles["clat"].to_numpy(), tiles["clon"].to_numpy(), tiles[cols], lookup)


def _prp(grid: Grid) -> pd.DataFrame:
    """Diviner PRP (south pole): ice and polar temperatures. Only hexagons with centre ≤ −80°
    (the product's 600×600 km square fully covers them)."""
    prp = pd.read_csv(RAW_MOON / "diviner_prp" / "dlre_prp_south.tab", usecols=[9, 10, 12, 13, 14],
                      names=["lon", "lat", "t_avg", "t_max", "ice"], header=0)
    idx = grid.index(latlon_to_cells(prp["lat"].to_numpy(), prp["lon"].to_numpy()))
    ice = prp["ice"].to_numpy()
    # Codes (checked against temperature, 2026-11-14): −999 = beyond 2.8738 m (lower bound → +∞);
    # 0 = ice stable at the surface; −1 = NOT in the label: it appears only in the coldest cells
    # (T max 52–99 K, colder than the "0" cells, ~106 K) → also ice stable at the surface
    # [interpretation from the data, verify in Paige et al. 2010].
    depth = np.where(ice == -999, np.inf, np.where(ice < 0, 0.0, ice))
    df = pd.DataFrame({"cell": idx, "depth": depth, "t_avg": prp["t_avg"].to_numpy(),
                       "t_max": prp["t_max"].to_numpy(),
                       "in1m": (depth <= 1.0).astype(float), "surf": (depth == 0).astype(float)})
    g = df.groupby("cell")
    agg = pd.DataFrame({"ice_frac_1m": g["in1m"].mean(), "ice_frac_surface": g["surf"].mean(),
                        "depth_med": g["depth"].median(), "prp_t_avg_2cm_K": g["t_avg"].median(),
                        "prp_t_max_K": g["t_max"].median()})
    out = pd.DataFrame(index=range(len(grid)),
                       columns=["ice_frac_1m", "ice_frac_surface", "ice_depth_m", "ice_depth_source",
                                "prp_t_avg_2cm_K", "prp_t_max_K"], dtype=float)
    valid = agg.index[grid.lat[agg.index] <= -80.0]
    a = agg.loc[valid]
    out.loc[valid, "ice_frac_1m"] = a["ice_frac_1m"].to_numpy()
    out.loc[valid, "ice_frac_surface"] = a["ice_frac_surface"].to_numpy()
    # median depth; "beyond 2.87 m" (lower bound) → NO_ICE_DEPTH_M, the Mars convention for "no ice found"
    out.loc[valid, "ice_depth_m"] = np.where(np.isfinite(a["depth_med"]), a["depth_med"], NO_ICE_DEPTH_M)
    out.loc[valid, "ice_depth_source"] = 1.0                                  # Diviner PRP model
    out.loc[valid, "prp_t_avg_2cm_K"] = a["prp_t_avg_2cm_K"].to_numpy()
    out.loc[valid, "prp_t_max_K"] = a["prp_t_max_K"].to_numpy()
    # Away from the poles water ice is not stable near the surface [physical assumption, verify].
    # 60–80° and the north pole stay NaN: no product in the kit says what happens there.
    low = np.abs(grid.lat) < 60.0
    out.loc[low, ["ice_frac_1m", "ice_frac_surface"]] = 0.0
    out.loc[low, "ice_depth_m"] = NO_ICE_DEPTH_M
    out.loc[low, "ice_depth_source"] = 3.0                                    # assumed
    return out


# --------------------------------------------------------------------------------------
# Permanent shadow (PGDA), composition (Lunar Prospector), rocks (Diviner), pits (LROC)
# --------------------------------------------------------------------------------------

def _psr(grid: Grid, step_m: float = 200.0) -> pd.Series:
    """Fraction of each hexagon in permanent shadow, south pole (PGDA LPSR, 0/1 mask at 20 m).
    Read at 200 m with an AVERAGE resampling → the value is the fraction of shadowed 20 m pixels."""
    import rasterio
    from rasterio.enums import Resampling
    with rasterio.open(RAW_MOON / "pgda_south_pole" / "LPSR_80S_20MPP_ADJ.TIF") as src:
        n = int(round(src.width * src.res[0] / step_m))
        frac = src.read(1, out_shape=(n, n), resampling=Resampling.average).astype(float)
        left, top = src.bounds.left, src.bounds.top
    frac = np.clip(frac, 0, 1)
    x = left + (np.arange(n) + 0.5) * step_m
    y = top - (np.arange(n) + 0.5) * step_m
    X, Y = np.meshgrid(x, y)
    rho = np.hypot(X, Y)
    lat = -(90.0 - np.degrees(2 * np.arctan(rho / (2 * MOON_RADIUS_M))))   # polar stereographic, k=1 at pole
    lon = np.degrees(np.arctan2(X, Y))
    k = 2 / (1 + np.sin(np.radians(-lat)))
    ok = np.isfinite(frac) & (lat <= -80.0)
    idx = grid.index(latlon_to_cells(lat[ok], lon[ok]))
    w = 1 / k[ok] ** 2                                                    # true area of each map pixel
    num, den = grid.sum(idx, w * frac[ok]), grid.sum(idx, w)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, num / den, np.nan)
    out[grid.lat > -80.4] = np.nan          # hexagons cut by the edge of the 80–90° S map
    return pd.Series(out, name="psr_frac")


def _composition(grid: Grid) -> pd.DataFrame:
    """Lunar Prospector GRS, 2° equal-area cells: value of the cell that contains the hexagon centre."""
    names = ("PIXEL_INDEX MIN_LAT MAX_LAT MIN_LON MAX_LON AM NEUTRON_DEN W_MGO W_AL2O3 W_SIO2 W_CAO "
             "TIO2 W_FEO W_K W_TH W_U").split()
    lp = pd.read_csv(RAW_MOON / "lunar_prospector_grs" / "lpgrs_high1_elem_abundance_2deg.tab",
                     sep=r"\s+", header=None, usecols=range(16), names=names)
    out = pd.DataFrame(index=range(len(grid)), dtype=float,
                       columns=["feo_wt_pct", "tio2_wt_pct", "al2o3_wt_pct", "mgo_wt_pct", "cao_wt_pct",
                                "silica_wt_pct", "k_ppm", "th_ppm", "u_ppm"])
    src = {"feo_wt_pct": ("W_FEO", 100), "tio2_wt_pct": ("TIO2", 100), "al2o3_wt_pct": ("W_AL2O3", 100),
           "mgo_wt_pct": ("W_MGO", 100), "cao_wt_pct": ("W_CAO", 100), "silica_wt_pct": ("W_SIO2", 100),
           "k_ppm": ("W_K", 1), "th_ppm": ("W_TH", 1), "u_ppm": ("W_U", 1)}
    lat, lon = grid.lat, grid.lon
    for (lo, hi), band in lp.groupby(["MIN_LAT", "MAX_LAT"]):
        in_band = (lat >= lo) & (lat < hi) if hi < 90 else (lat >= lo)
        if not in_band.any():
            continue
        band = band.sort_values("MIN_LON")
        edges = band["MIN_LON"].to_numpy()
        j = np.clip(np.searchsorted(edges, lon[in_band], side="right") - 1, 0, len(band) - 1)
        rows = band.iloc[j]
        for col, (c, f) in src.items():
            out.loc[in_band, col] = rows[c].to_numpy() * f
    return out


def _rocks(grid: Grid, rows_per_chunk: int = 512) -> pd.Series:
    """Diviner rock abundance (fraction, ±60°, 32 px/deg) → area-weighted mean × 100 (%)."""
    ppd, nl, ns = 32, 3840, 11520
    ra = np.memmap(RAW_MOON / "diviner_rocks" / "dgdr_ra_avg_cyl_032_img.img", dtype="<i2", mode="r",
                   shape=(nl, ns))
    lon = (np.arange(ns) + 0.5) / ppd
    n = len(grid)
    num, den = np.zeros(n), np.zeros(n)
    for r0 in range(0, nl, rows_per_chunk):
        rows = np.arange(r0, min(r0 + rows_per_chunk, nl))
        lat = 60.0 - (rows + 0.5) / ppd
        dn = ra[rows[0]: rows[-1] + 1].ravel()
        ok = dn != -32768
        LAT, LON = np.repeat(lat, ns)[ok], np.tile(lon, rows.size)[ok]
        idx = grid.index(latlon_to_cells(LAT, LON))
        w = _area_weight(LAT)
        num += grid.sum(idx, w * dn[ok] * 0.001)
        den += grid.sum(idx, w)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, 100 * num / den, np.nan)
    out[np.abs(grid.lat) > 59.5] = np.nan
    return pd.Series(out, name="rock_abundance_pct")


def _unit_vectors(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def _pits(grid: Grid) -> pd.DataFrame:
    pits = pd.read_csv(RAW_MOON / "lroc_pits" / "lroc_pits_list.csv")
    lat, lon = pits["Lat."].to_numpy(float), pits["Long."].to_numpy(float)
    idx = grid.index(latlon_to_cells(lat, lon))
    count = np.bincount(idx, minlength=len(grid))
    p = _unit_vectors(lat, lon)
    c = _unit_vectors(grid.lat, grid.lon)
    best = np.full(len(grid), -1.0)
    for s in range(0, len(grid), 50_000):                        # max cos(angle) to any pit
        best[s:s + 50_000] = (c[s:s + 50_000] @ p.T).max(axis=1)
    dist = np.arccos(np.clip(best, -1, 1)) * MOON_RADIUS_M / 1000
    return pd.DataFrame({"pit_count": count, "pit_dist_km": dist, "caves": (count > 0).astype(int)})


# --------------------------------------------------------------------------------------
# Main entry points
# --------------------------------------------------------------------------------------

def build_moon_grid(log=print) -> pd.DataFrame:
    """The whole-Moon card grid (one row per H3 res-4 hexagon). Writes data/processed/."""
    import h3
    log(f"H3 grid, res {H3_RES}…")
    grid = Grid(H3_RES)
    log(f"  {len(grid):,} hexagons")
    parts = [pd.DataFrame({"h3": [h3.int_to_str(int(c)) for c in grid.ids], "lat": grid.lat, "lon": grid.lon})]
    for name, fn in [("relief (LOLA)", _relief), ("temperature (Diviner GCP)", _temperature),
                     ("ice and polar temperature (Diviner PRP)", _prp), ("permanent shadow (PGDA)", _psr),
                     ("composition (Lunar Prospector)", _composition), ("rocks (Diviner)", _rocks),
                     ("pits (LROC)", _pits)]:
        log(f"{name}…")
        part = fn(grid)
        parts.append(part.to_frame() if isinstance(part, pd.Series) else part)
    df = pd.concat(parts, axis=1)
    sun = 90.0 - np.maximum(0.0, np.abs(df["lat"]) - MOON_OBLIQUITY_DEG)
    df["sun_elev_max_deg"] = sun.where(np.abs(df["lat"]) < SUN_FORMULA_MAX_LAT)   # poles: see psr_frac
    df["precip_mm_year"] = 0.0
    df["dust_aod"] = np.nan

    PROCESSED.mkdir(parents=True, exist_ok=True)
    keep = {"h3", "lat", "lon"}
    df = df.astype({c: "float32" for c in df.columns if c not in keep})
    df.to_parquet(PROCESSED / f"luna_h3r{H3_RES}.parquet", index=False)
    pd.DataFrame([(k, *v) for k, v in COLUMNS.items()], columns=["column", "unit", "source", "method"]) \
        .to_csv(PROCESSED / f"luna_h3r{H3_RES}_columnas.csv", index=False)
    return df


def build_moon_targets(grid_df: pd.DataFrame) -> pd.DataFrame:
    """Card of every Moon target site = the card of the H3 res-4 cell (~12 km) that contains it.
    Same shape as mars_grid.build_mars_targets: id, name, body, lat/lon OF THE SITE, type, h3 + card."""
    import re

    import h3
    sites = pd.read_csv(CATALOGS / "target_sites.csv")
    sites = sites[sites["body"] == "moon"].dropna(subset=["lat", "lon"]).reset_index(drop=True)
    by_h3 = grid_df.set_index("h3")
    rows = []
    for s in sites.itertuples():
        cell = h3.latlng_to_cell(float(s.lat), ((float(s.lon) + 180) % 360) - 180, H3_RES)
        card = by_h3.loc[cell].drop(["lat", "lon"]).to_dict()
        rows.append({"id": re.sub(r"[^a-z0-9]+", "_", s.name.lower()).strip("_"), "name": s.name,
                     "body": "moon", "lat": float(s.lat), "lon": float(s.lon), "type": s.type,
                     "h3": cell, **card})
    out = pd.DataFrame(rows)
    out.to_parquet(PROCESSED / "fichas_objetivos_moon.parquet", index=False)
    out.to_csv(PROCESSED / "fichas_objetivos_moon.csv", index=False, float_format="%.4g")
    return out
