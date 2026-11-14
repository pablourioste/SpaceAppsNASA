"""Pack data/raw/<body>/ into one zip per dataset, ready to attach to a GitHub Release.

    python scripts/pack_data.py mars --out C:\\some\\folder

Each zip keeps the path below data/raw/, so whoever downloads it just unzips it into
data/raw/ and every file lands in the right place, e.g.

    mars_mola_128ppd.zip  →  mars/mola_megdr_128ppd/megt44n000hb.img …

Datasets are defined in src/analogs/download.py; several folders can share one zip.
"""
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analogs.paths import RAW  # noqa: E402

# zip name → folders under data/raw/<body>/
PACKS = {
    "mars": {
        "mars_mola_16ppd.zip": ["mola_megdr_16ppd"],
        "mars_mola_128ppd.zip": ["mola_megdr_128ppd"],
        "mars_tes_thermal_inertia.zip": ["tes_thermal_inertia"],
        "mars_grs.zip": ["grs_special", "grs_elements"],
        "mars_tes_atmos_my26.zip": ["tes_atmos_my26"],
    },
}


def pack(body: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for zip_name, folders in PACKS[body].items():
        target = out / zip_name
        files = [f for folder in folders for f in sorted((RAW / body / folder).rglob("*"))
                 if f.is_file() and not f.name.endswith(".part")]
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in files:
                z.write(f, f.relative_to(RAW).as_posix())
        raw_mb = sum(f.stat().st_size for f in files) / 1e6
        print(f"{zip_name:32s} {len(files):3d} files  {raw_mb:8.1f} MB → {target.stat().st_size / 1e6:8.1f} MB")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("body", choices=sorted(PACKS))
    p.add_argument("--out", type=Path, required=True, help="folder for the zips (keep it outside OneDrive)")
    args = p.parse_args()
    pack(args.body, args.out)
