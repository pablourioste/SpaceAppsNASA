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


def download(keys: list[str] | None = None) -> None:
    """Download the given datasets (all of them if keys is None) into data/raw/."""
    keys = keys or list(DATASETS)
    unknown = [k for k in keys if k not in DATASETS]
    if unknown:
        raise KeyError(f"Unknown dataset(s): {unknown}. Available: {list(DATASETS)}")

    with requests.Session() as session:
        session.headers["User-Agent"] = "earth-analogs-spaceapps/0.1 (python-requests)"
        for key in keys:
            ds = DATASETS[key]
            ds.dest.mkdir(parents=True, exist_ok=True)
            print(f"\n[{ds.key}] {ds.description}\n  → {ds.dest}")
            for name in ds.files:
                status = _download_file(session, f"{ds.base_url}/{name}", ds.dest / name)
                print(f"  {name}: {status}")


def download_all() -> None:
    """Everything implemented so far (Mars). Moon and Earth downloads are still to do."""
    download()
