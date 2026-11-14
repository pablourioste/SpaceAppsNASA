"""Mars: read the raw PDS products and extract the variables at each target site.

    python scripts/build_mars_features.py

Inputs (data/raw/mars/, see scripts/download_data.py):
    mola_megdr_16ppd/      MOLA MEGDR topography, 16 px/deg
    tes_thermal_inertia/   TES thermal inertia, day + night, 20 px/deg
    grs_elements/          GRS element maps, 5°×5° (H2O, Cl, Fe, Si, K, Th)
    grs_special/           GRS neutron spectrometer maps, 0.5° grid
    tes_atmos_my26/        TES IR retrievals for Mars Year 26 (dust, ice, T_surf, P_surf)

Outputs:
    data/interim/mars_tes_atmos_2deg.parquet      TES atmosphere binned on a 2° grid (reusable for maps)
    data/processed/fichas_objetivos_mars.parquet  one row per Mars target site
    outputs/validation/mars_sites_features.csv    the same, for people to read

Conventions (data/README.md): latitude planetocentric, longitude −180…180 east, SI units.

Scale (docs/decisions 006): every variable is taken over the same ~10 km site footprint;
datasets coarser than that (GRS, TES atmosphere) give the value of the cell that contains the
site, i.e. regional context.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import CATALOGS, INTERIM, PROCESSED, RAW, VALIDATION

MARS_RADIUS_M = 3_389_500.0     # mean radius (IAU), used for distances on the grid
MARS_OBLIQUITY_DEG = 25.19
FOOTPRINT_DIAMETER_KM = 10.0    # site footprint (docs/03_enfoque.md, decision 006)

# TES IR dust optical depth is absorption at 9.3 µm; Earth AOD (MODIS) is visible extinction.
# Montabone et al. (2015) use ×2.6 to go from 9.3 µm absorption to visible extinction. [verify]
DUST_IR_TO_VIS = 2.6

RAW_MARS = RAW / "mars"


# --------------------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------------------

def _label_values(lbl: Path) -> dict[str, str]:
    text = lbl.read_text(errors="replace")
    out = {}
    for key, value in re.findall(r"^\s*([A-Z_]+)\s*=\s*\"?([^\"\r\n]*)", text, re.M):
        out.setdefault(key, value.strip())
    return out


@dataclass
class GlobalGrid:
    """A global simple-cylindrical raster with planetocentric latitude."""

    values: np.ndarray          # (lines, samples), float, NaN = no data
    max_lat: float              # latitude of the top edge
    west_lon: float             # longitude of the left edge (0 or −180)
    ppd: float                  # pixels per degree

    def row_col(self, lat: float, lon: float) -> tuple[int, int]:
        lon = (lon - self.west_lon) % 360.0
        row = int(np.clip(np.floor((self.max_lat - lat) * self.ppd), 0, self.values.shape[0] - 1))
        col = int(np.floor(lon * self.ppd)) % self.values.shape[1]
        return row, col

    def window(self, lat: float, lon: float, diameter_km: float = FOOTPRINT_DIAMETER_KM) -> np.ndarray:
        """Values of the pixels whose centre is within diameter/2 of the site (at least 3×3)."""
        row, col = self.row_col(lat, lon)
        px_km = np.deg2rad(1 / self.ppd) * MARS_RADIUS_M / 1000
        half = max(1, int(np.ceil(diameter_km / 2 / px_km)))
        rows = np.clip(np.arange(row - half, row + half + 1), 0, self.values.shape[0] - 1)
        cols = np.arange(col - half, col + half + 1) % self.values.shape[1]
        return self.values[np.ix_(rows, cols)]


def read_pds3_image(img: Path, nodata: float | None = None) -> GlobalGrid:
    """Read a PDS3 simple-cylindrical image using its detached .lbl."""
    lab = _label_values(img.with_suffix(".lbl"))
    lines, samples = int(lab["LINES"]), int(lab["LINE_SAMPLES"])
    bits = int(lab["SAMPLE_BITS"])
    stype = lab["SAMPLE_TYPE"]
    order = ">" if ("MSB" in stype or "SUN" in stype) else "<"
    kind = "f" if "REAL" in stype else ("u" if "UNSIGNED" in stype or bits == 8 else "i")
    data = np.fromfile(img, dtype=np.dtype(f"{order}{kind}{bits // 8}")).reshape(lines, samples)
    values = data.astype("float32")
    if nodata is not None:
        values[data == nodata] = np.nan
    first = lambda k: float(re.match(r"[-\d.]+", lab[k]).group())  # noqa: E731
    return GlobalGrid(values, first("MAXIMUM_LATITUDE"), first("WESTERNMOST_LONGITUDE"), first("MAP_RESOLUTION"))


def read_grs_table(tab: Path, lat_col: int, lon_col: int, value_col: int, nodata_below: float = -99,
                   nodata_above: float = 9000) -> pd.DataFrame:
    """GRS ASCII tables → DataFrame(lat, lon[−180…180], value)."""
    # Some tables are comma-separated, others space-separated, with leading blanks
    text = tab.read_text(errors="replace").replace(",", " ")
    df = pd.read_csv(io.StringIO(text), sep=r"\s+", header=None)
    out = pd.DataFrame({"lat": df[lat_col], "lon": df[lon_col], "value": df[value_col].astype(float)})
    out.loc[(out["value"] <= nodata_below) | (out["value"] >= nodata_above), "value"] = np.nan
    out["lon"] = ((out["lon"] + 180) % 360) - 180
    return out


def _grs_unit(lbl: Path) -> str:
    units = re.findall(r'UNIT\s*=\s*"([^"]+)"', lbl.read_text(errors="replace"))
    return units[2] if len(units) > 2 else ""


def nearest_cell(df: pd.DataFrame, lat: float, lon: float) -> float:
    """Value of the grid cell closest to the site (cells are small enough that this is exact)."""
    dlon = np.abs(((df["lon"].to_numpy() - lon) + 180) % 360 - 180)
    d = (df["lat"].to_numpy() - lat) ** 2 + (dlon * np.cos(np.deg2rad(lat))) ** 2
    return float(df["value"].to_numpy()[np.argmin(d)])


# --------------------------------------------------------------------------------------
# Derived fields
# --------------------------------------------------------------------------------------

def slope_map(dem: GlobalGrid) -> GlobalGrid:
    """Slope (degrees) from a planetocentric DEM, with the true metric pixel size at each latitude."""
    z = dem.values
    n_lines = z.shape[0]
    lat = dem.max_lat - (np.arange(n_lines) + 0.5) / dem.ppd
    d = np.deg2rad(1 / dem.ppd) * MARS_RADIUS_M                   # metres per pixel north-south
    dzdy = np.gradient(z, d, axis=0)
    dx = d * np.clip(np.cos(np.deg2rad(lat)), 1e-3, None)[:, None]  # metres per pixel east-west
    dzdx = (np.roll(z, -1, axis=1) - np.roll(z, 1, axis=1)) / (2 * dx)  # wraps around in longitude
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy))).astype("float32")
    return GlobalGrid(slope, dem.max_lat, dem.west_lon, dem.ppd)


def sun_elevation_max(lat_deg: float, obliquity_deg: float = MARS_OBLIQUITY_DEG) -> float:
    """Highest noon Sun elevation over a year at this latitude (flat horizon)."""
    return float(90.0 - max(0.0, abs(lat_deg) - obliquity_deg))


def bin_tes_atmosphere(folder: Path, cell_deg: float = 2.0) -> pd.DataFrame:
    """Bin all TES IR retrievals of the year onto a regular grid.

    MGS was sun-synchronous: observations are at ~14 h (day) and ~02 h (night) local time.
    """
    cols = ["LON", "LAT", "LTST", "IR_CDOD", "IR_CWIOD", "TSURF", "PSURF"]
    parts = []
    for dat in sorted(folder.glob("TES_COD_IR_*.dat")):
        parts.append(pd.read_csv(dat, sep=r"\s+", usecols=cols))
    df = pd.concat(parts, ignore_index=True)
    df["LON"] = ((df["LON"] + 180) % 360) - 180
    df["lat_bin"] = np.floor((df["LAT"] + 90) / cell_deg).astype(int)
    df["lon_bin"] = np.floor((df["LON"] + 180) / cell_deg).astype(int)
    df["is_day"] = df["LTST"].between(10, 18)
    df["is_night"] = (df["LTST"] < 6) | (df["LTST"] >= 20)

    g = df.groupby(["lat_bin", "lon_bin"])
    out = pd.DataFrame({
        "n_obs": g.size(),
        "dust_od_9um_mean": g["IR_CDOD"].mean(),
        "ice_od_12um_mean": g["IR_CWIOD"].mean(),
        "p_surf_Pa_mean": g["PSURF"].mean(),
    })
    day, night = df[df["is_day"]].groupby(["lat_bin", "lon_bin"]), df[df["is_night"]].groupby(["lat_bin", "lon_bin"])
    out["t_day_K_mean"] = day["TSURF"].mean()
    out["t_day_K_p95"] = day["TSURF"].quantile(0.95)
    out["t_night_K_mean"] = night["TSURF"].mean()
    out["t_night_K_p05"] = night["TSURF"].quantile(0.05)
    out = out.reset_index()
    out["lat"] = -90 + (out["lat_bin"] + 0.5) * cell_deg
    out["lon"] = -180 + (out["lon_bin"] + 0.5) * cell_deg
    out.attrs["n_retrievals"] = len(df)
    return out


def _atmos_at(atmos: pd.DataFrame, lat: float, lon: float, cell_deg: float = 2.0) -> pd.Series:
    """Row of the 2° atmosphere grid that contains the site (NaNs if the cell has no data)."""
    lat_bin = int(np.floor((lat + 90) / cell_deg))
    lon_bin = int(np.floor((((lon + 180) % 360)) / cell_deg))
    hit = atmos[(atmos["lat_bin"] == lat_bin) & (atmos["lon_bin"] == lon_bin)]
    return hit.iloc[0] if len(hit) else pd.Series(dtype=float)


# --------------------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------------------

def _nanmedian(a: np.ndarray) -> float:
    return float(np.nanmedian(a)) if np.isfinite(a).any() else np.nan


def build_mars_targets(sites: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per Mars target site with every variable we can compute today."""
    if sites is None:
        sites = pd.read_csv(CATALOGS / "target_sites.csv")
    sites = sites[sites["body"] == "mars"].dropna(subset=["lat", "lon"]).reset_index(drop=True)

    # --- Topography: MOLA → slope and roughness at the MEGDR baseline (~3.7 km) ---
    dem = read_pds3_image(RAW_MARS / "mola_megdr_16ppd" / "megt90n000eb.img")
    slope = slope_map(dem)

    # --- TES thermal inertia (0 = no data); keep only measured (not interpolated) pixels if any ---
    ti, ti_mask = {}, {}
    for when in ("day", "night"):
        ti[when] = read_pds3_image(RAW_MARS / "tes_thermal_inertia" / f"global_ti_{when}_2007.img", nodata=0)
        ti_mask[when] = read_pds3_image(RAW_MARS / "tes_thermal_inertia" / f"global_ti_msk_{when}_2007.img")

    # --- GRS element maps (5°×5°) and neutron flux (0.5°) ---
    grs_dir = RAW_MARS / "grs_elements"
    elements = {}
    for name in ["h2o", "cl", "fe", "si", "k", "th"]:
        tab = grs_dir / f"{name}_sr_5x5.tab"
        elements[name] = (read_grs_table(tab, lat_col=0, lon_col=1, value_col=2), _grs_unit(tab.with_suffix(".lbl")))
    epithermal = read_grs_table(RAW_MARS / "grs_special" / "ns_epithermal_020917.tab", lat_col=1, lon_col=0, value_col=2)

    # --- TES atmosphere (Mars Year 26), binned once on a 2° grid and cached ---
    atmos_cache = INTERIM / "mars_tes_atmos_2deg.parquet"
    if atmos_cache.exists():
        atmos = pd.read_parquet(atmos_cache)
    else:
        atmos = bin_tes_atmosphere(RAW_MARS / "tes_atmos_my26")
        INTERIM.mkdir(parents=True, exist_ok=True)
        atmos.to_parquet(atmos_cache, index=False)

    rows = []
    for s in sites.itertuples():
        lat, lon = float(s.lat), float(s.lon)
        sl = slope.window(lat, lon)
        row = {
            "id": re.sub(r"[^a-z0-9]+", "_", s.name.lower()).strip("_"),
            "name": s.name, "body": "mars", "lat": lat, "lon": lon, "type": s.type,
            # variables.yaml columns
            "slope_deg": _nanmedian(sl),
            "roughness_deg": float(np.sqrt(np.nanmean(sl ** 2))),   # RMS slope over the footprint
            "sun_elev_max_deg": sun_elevation_max(lat),
        }
        a = _atmos_at(atmos, lat, lon)
        t_day, t_night = a.get("t_day_K_mean", np.nan), a.get("t_night_K_mean", np.nan)
        row["t_mean_K"] = float((t_day + t_night) / 2)        # mean of ~14 h and ~02 h → diurnal mean (approx.)
        row["t_max_K"] = float(a.get("t_day_K_p95", np.nan))   # 95th percentile of afternoon T_surf over the year
        row["dust_aod"] = float(a.get("dust_od_9um_mean", np.nan) * DUST_IR_TO_VIS)

        # Extra Mars-only columns (not in variables.yaml yet; kept for the card and for Science)
        row["elevation_m"] = _nanmedian(dem.window(lat, lon))
        for when in ("day", "night"):
            vals, msk = ti[when].window(lat, lon), ti_mask[when].window(lat, lon)
            measured = np.where(msk == 1, vals, np.nan)
            row[f"thermal_inertia_{when}_SI"] = _nanmedian(measured) if np.isfinite(measured).any() else _nanmedian(vals)
        for name, (df, unit) in elements.items():
            suffix = "ppm" if "PPM" in unit.upper() else "wt_pct"
            row[f"grs_{name}_{suffix}"] = nearest_cell(df, lat, lon)
        row["ns_epithermal_cps"] = nearest_cell(epithermal, lat, lon)
        row["t_day_K"], row["t_night_K"] = float(t_day), float(t_night)
        row["dust_od_9um"] = float(a.get("dust_od_9um_mean", np.nan))
        row["ice_od_12um"] = float(a.get("ice_od_12um_mean", np.nan))
        row["p_surf_Pa"] = float(a.get("p_surf_Pa_mean", np.nan))
        row["tes_atmos_n_obs"] = float(a.get("n_obs", np.nan))
        rows.append(row)

    out = pd.DataFrame(rows)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / "fichas_objetivos_mars.parquet", index=False)
    out.round(3).to_csv(VALIDATION / "mars_sites_features.csv", index=False)
    return out
