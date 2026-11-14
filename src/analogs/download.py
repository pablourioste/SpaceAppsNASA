"""STEP 1: download the data from the archives  →  data/raw/{earth,moon,mars}/

Rules:
- Download ONLY what is needed: L3/L4 products (already a physical variable).
- Every downloaded dataset is recorded in the inventory in data/README.md.
- No passwords in the code: earthaccess asks for them or reads ~/.netrc.

Usage:
    python scripts/download_data.py                 # everything implemented so far
    python scripts/download_data.py mola tes        # only some datasets
    python scripts/download_data.py --list          # list datasets and sizes

Files that already exist with the expected size are skipped, so it is safe to re-run.

Earth example (Earthdata; needs an Earthdata Login account), still to do:

    import earthaccess
    earthaccess.login()
    res = earthaccess.search_data(short_name="MOD11C3", temporal=("2023-01", "2023-12"))
    earthaccess.download(res, RAW / "earth" / "modis_lst")
"""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import requests
from tqdm import tqdm

from .paths import RAW

# Some networks (proxies, antivirus) break certifi's certificate check. truststore makes
# Python use the operating system's certificate store instead, if it is installed.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

PDS_GEO = "https://pds-geosciences.wustl.edu"


@dataclass
class Dataset:
    key: str
    body: str
    folder: str
    description: str
    base_url: str
    files: list[str] = field(default_factory=list)

    @property
    def dest(self) -> Path:
        return RAW / self.body / self.folder


# --- Mars (PDS Geosciences Node, no account needed) ---------------------------------------

_MOLA = f"{PDS_GEO}/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg016"
_TES = f"{PDS_GEO}/mgs/mgs-m-tes-5-timap-v1/mgst_9001/data"
_GRS_SPECIAL = f"{PDS_GEO}/ody/urn-nasa-pds-odyssey_grs_special/data"
_GRS_ELEMENTS = f"{PDS_GEO}/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed"
_TES_ATMOS = "https://atmos.nmsu.edu/PDS/data/PDS4/mgs_tes_atmos_dust-ice/data_IR_Aerosol_Optical_Depth/MY26"
# Mars Year 26 (2002–2004): a full year without a global dust storm (MY25 had one in 2001)
_TES_ATMOS_STEMS = [f"TES_COD_IR_MY26_Ls{a:03d}_Ls{a + 30:03d}" for a in range(0, 360, 30)]
_MOLA128 = f"{PDS_GEO}/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128"


def mola128_tile(lat: float, lon: float) -> str:
    """Name of the MOLA MEGDR 128 px/deg tile that contains a point, e.g. '44n270'.

    Tiles are 44° × 90°: latitude bands 88N–44N ('88n'), 44N–0 ('44n'), 0–44S ('00n'),
    44S–88S ('44s'); longitude 0–90, 90–180, 180–270, 270–360 east. Poles (|lat| > 88°) use
    polar products instead and are not covered here.
    """
    if abs(lat) > 88:
        raise ValueError(f"lat={lat}: beyond the 128 ppd equatorial tiles (|lat| ≤ 88°)")
    band = "88n" if lat >= 44 else "44n" if lat >= 0 else "00n" if lat >= -44 else "44s"
    lon_east = lon % 360
    return f"{band}{int(lon_east // 90) * 90:03d}"


MOLA128_ALL_TILES = [f"{band}{lon:03d}" for band in ("88n", "44n", "00n", "44s") for lon in (0, 90, 180, 270)]


def _mola128_all_files() -> list[str]:
    """All 16 tiles (whole planet between ±88°): needed to click any point of Mars (decision 007)."""
    return _with_labels([f"meg{kind}{t}hb" for t in MOLA128_ALL_TILES for kind in ("t", "c")],
                        "img", ["xml", "lbl", "hdr"])


def _mola128_files() -> list[str]:
    """Topography (megt) + shots per cell (megc) tiles for every Mars target site."""
    import pandas as pd  # local import: only needed for this dataset

    from .paths import CATALOGS

    sites = pd.read_csv(CATALOGS / "target_sites.csv")
    sites = sites[sites["body"] == "mars"].dropna(subset=["lat", "lon"])
    tiles = sorted({mola128_tile(r.lat, r.lon) for r in sites.itertuples()})
    return _with_labels([f"meg{kind}{t}hb" for t in tiles for kind in ("t", "c")], "img", ["xml", "lbl", "hdr"])


def _with_labels(stems: list[str], data_ext: str, label_exts: list[str]) -> list[str]:
    return [f"{s}.{e}" for s in stems for e in [data_ext, *label_exts]]


DATASETS: dict[str, Dataset] = {
    "mola": Dataset(
        key="mola",
        body="mars",
        folder="mola_megdr_16ppd",
        description="MGS MOLA MEGDR, 16 px/deg (~3.7 km): topography (megt) + counts per cell (megc)",
        base_url=_MOLA,
        # megt = topography (radius − areoid, m); megc = number of laser shots per cell (QC)
        files=_with_labels(["megt90n000eb", "megc90n000eb"], "img", ["xml", "lbl", "hdr"]),
    ),
    "mola128": Dataset(
        key="mola128",
        body="mars",
        folder="mola_megdr_128ppd",
        description="MGS MOLA MEGDR, 128 px/deg (~463 m): only the 44°×90° tiles that contain a Mars "
                    "target site. Topography (megt, 130 MB/tile) + shots per cell (megc, 65 MB/tile)",
        base_url=_MOLA128,
        files=[],  # filled lazily from data/catalogs/target_sites.csv (see download())
    ),
    "mola128_all": Dataset(
        key="mola128_all",
        body="mars",
        folder="mola_megdr_128ppd",   # same folder as "mola128": tiles already there are skipped
        description="MGS MOLA MEGDR, 128 px/deg (~463 m): ALL 16 tiles (whole planet between ±88°), "
                    "~3.1 GB in total. Needed to click any point of Mars (decision 007)",
        base_url=_MOLA128,
        files=[],  # filled lazily (see download())
    ),
    "mola_polar": Dataset(
        key="mola_polar",
        body="mars",
        folder="mola_megdr_polar128",
        description="MGS MOLA MEGDR polar maps, 128 px/deg (460 m/px), polar stereographic, north (37.45°N→90°) "
                    "and south (90°S→37.45°S): topography (megt, 210 MB) + shots per cell (megc, 105 MB). "
                    "Covers the poles that the 128 px/deg tiles leave out (|lat| > 88°)",
        base_url=f"{PDS_GEO}/mgs/urn-nasa-pds-mgs_mola_topography_derived/polar",
        files=_with_labels(["megt_n_128_1", "megt_s_128_1", "megc_n_128", "megc_s_128"], "img", ["lbl", "xml"]),
    ),
    "swim": Dataset(
        key="swim",
        body="mars",
        folder="swim2_ice",
        description="SWIM 2.0 (NASA Mars Exploration Program / PSI) combined ice-consistency maps for "
                    "ice at 0–1 m, 1–5 m and >5 m depth, ±60° latitude, GeoTIFF (→ ice_depth_m)",
        base_url="https://swim.psi.edu/output/SWIM2/Global/Composite",
        files=["SWIM2_c0_1.tif", "SWIM2_c1_5.tif", "SWIM2_c_5.tif"],
    ),
    "mcs_tsurf": Dataset(
        key="mcs_tsurf",
        body="mars",
        folder="mcs_tsurf_my31",
        description="MRO MCS surface temperature day (~15 h) and night (~03 h), Mars Year 31, one Earth "
                    "day in 10, T_surf columns only (→ t_mean_K). See src/analogs/mcs.py",
        base_url="https://atmos.nmsu.edu/PDS/data",
        files=[],  # custom: sampled and reduced by analogs.mcs.download_mcs_tsurf
    ),
    "tes": Dataset(
        key="tes",
        body="mars",
        folder="tes_thermal_inertia",
        description="MGS TES thermal inertia maps (Putzig & Mellon 2007), day + night + interpolation masks",
        base_url=_TES,
        files=["datainfo.txt"]
        + _with_labels(
            ["global_ti_day_2007", "global_ti_night_2007",
             "global_ti_msk_day_2007", "global_ti_msk_night_2007"],
            "img", ["lbl"],
        ),
    ),
    "grs": Dataset(
        key="grs",
        body="mars",
        folder="grs_special",
        description="Odyssey GRS special products (2002): neutron flux maps (NS + HEND)",
        base_url=_GRS_SPECIAL,
        files=_with_labels(
            ["ns_epithermal_020917", "ns_thermal_020917", "ns_fast_020917",
             "hend_epithermal_020917", "hend_fast_020917"],
            "tab", ["xml", "lbl"],
        ),
    ),
    "grs_elements": Dataset(
        key="grs_elements",
        body="mars",
        folder="grs_elements",
        description="Odyssey GRS element concentration maps, smoothed 5°×5°: H2O, Cl, Fe, Si, K, Th, K/Th",
        base_url=_GRS_ELEMENTS,
        files=_with_labels(
            ["h2o_sr_5x5", "cl_sr_5x5", "fe_sr_5x5", "si_sr_5x5", "k_sr_5x5", "th_sr_5x5", "kvsth_sr_5x5"],
            "tab", ["lbl", "xml"],
        ),
    ),
    "tes_atmos": Dataset(
        key="tes_atmos",
        body="mars",
        folder="tes_atmos_my26",
        description="MGS TES IR retrievals, Mars Year 26 (Montabone et al., PDS Atmospheres): "
                    "column dust and water-ice optical depth, surface temperature, surface pressure",
        base_url=_TES_ATMOS,
        files=_with_labels(_TES_ATMOS_STEMS, "dat", ["xml"]),
    ),
}


def _remote_size(session: requests.Session, url: str) -> int | None:
    r = session.head(url, allow_redirects=True, timeout=60)
    r.raise_for_status()
    size = r.headers.get("Content-Length")
    return int(size) if size else None


def _download_file(session: requests.Session, url: str, path: Path) -> str:
    expected = _remote_size(session, url)
    if path.exists() and expected is not None and path.stat().st_size == expected:
        return "skipped (already there)"

    tmp = path.with_suffix(path.suffix + ".part")
    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f, tqdm(total=expected, unit="B", unit_scale=True,
                                        desc=path.name, leave=False) as bar:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bar.update(len(chunk))
    if expected is not None and tmp.stat().st_size != expected:
        tmp.unlink()
        raise IOError(f"{path.name}: size mismatch (expected {expected} bytes)")
    tmp.replace(path)
    return f"downloaded ({path.stat().st_size / 1e6:.1f} MB)"


MANIFEST_FIELDS = ["dataset", "file", "url", "bytes", "status", "downloaded"]


def _write_manifest(body: str, rows: list[dict]) -> Path:
    """data/raw/<body>/MANIFEST.csv, same format as scripts/download_moon.py.

    `dataset` is the folder under data/raw/<body>/. Rows from earlier runs that were not
    touched this time are kept, so downloading one dataset does not erase the others.
    """
    path = RAW / body / "MANIFEST.csv"
    old = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            old = {(r["dataset"], r["file"]): r for r in csv.DictReader(f)}
    now = dt.datetime.now().isoformat(timespec="seconds")
    for r in rows:
        old[(r["dataset"], r["file"])] = {**r, "downloaded": now}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for key in sorted(old):
            w.writerow(old[key])
    return path


def download(keys: list[str] | None = None) -> None:
    """Download the given datasets (all of them if keys is None) into data/raw/.

    At the end, writes data/raw/<body>/MANIFEST.csv (which file, from which URL, how many
    bytes and when), like scripts/download_moon.py does for the Moon.
    """
    # By default skip "mola128" (only the tiles with target sites): "mola128_all" includes them
    keys = keys or [k for k in DATASETS if k != "mola128"]
    unknown = [k for k in keys if k not in DATASETS]
    if unknown:
        raise KeyError(f"Unknown dataset(s): {unknown}. Available: {list(DATASETS)}")

    rows: dict[str, list[dict]] = {}
    with requests.Session() as session:
        session.headers["User-Agent"] = "earth-analogs-spaceapps/0.1 (python-requests)"
        for key in keys:
            ds = DATASETS[key]
            if key == "mola128" and not ds.files:
                ds.files = _mola128_files()
            if key == "mola128_all" and not ds.files:
                ds.files = _mola128_all_files()
            ds.dest.mkdir(parents=True, exist_ok=True)
            print(f"\n[{ds.key}] {ds.description}\n  → {ds.dest}")
            if key == "mcs_tsurf":
                from .mcs import download_mcs_tsurf
                rows.setdefault(ds.body, []).extend(download_mcs_tsurf(ds.dest, session=session))
                continue
            for name in ds.files:
                url = f"{ds.base_url}/{name}"
                try:
                    status = _download_file(session, url, ds.dest / name)
                    manifest_status = "ya estaba" if status.startswith("skipped") else "ok"
                except Exception as e:  # keep going; the error is recorded in the manifest
                    status = manifest_status = f"ERROR {type(e).__name__}: {str(e)[:120]}"
                path = ds.dest / name
                rows.setdefault(ds.body, []).append({
                    "dataset": ds.folder, "file": name, "url": url,
                    "bytes": path.stat().st_size if path.exists() else 0, "status": manifest_status,
                })
                print(f"  {name}: {status}")

    for body, body_rows in rows.items():
        path = _write_manifest(body, body_rows)
        errors = [r for r in body_rows if r["status"].startswith("ERROR")]
        total = sum(r["bytes"] for r in body_rows) / 1e9
        print(f"\n{body}: {len(body_rows) - len(errors)} ok, {len(errors)} with errors, "
              f"{total:.2f} GB → {path}")
        for r in errors:
            print(f"  ✗ {r['dataset']}/{r['file']}: {r['status']}")


def download_all() -> None:
    """Everything implemented so far (Mars). Moon and Earth downloads are still to do."""
    download()
