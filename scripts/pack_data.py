"""Pack data/raw/<body>/ into one zip per dataset, ready to attach to a GitHub Release.

    python scripts/pack_data.py mars --out C:\\some\\folder
    python scripts/pack_data.py earth --out E:\\          # straight to a USB stick
    python scripts/pack_data.py tables --out E:\\         # only the processed tables (enough for buscar.py)

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

from analogs.paths import DATA, RAW  # noqa: E402

# zip name → folders under data/raw/<body>/
PACKS = {
    "mars": {
        "mars_mola_16ppd.zip": ["mola_megdr_16ppd"],
        "mars_mola_128ppd.zip": ["mola_megdr_128ppd"],
        "mars_tes_thermal_inertia.zip": ["tes_thermal_inertia"],
        "mars_grs.zip": ["grs_special", "grs_elements"],
        "mars_tes_atmos_my26.zip": ["tes_atmos_my26"],
        "mars_mola_polar128.zip": ["mola_megdr_polar128"],
        "mars_swim2_ice.zip": ["swim2_ice"],
        "mars_mcs_tsurf_my31.zip": ["mcs_tsurf_my31"],
    },
    # Folders as written by scripts/download_moon.py (see data/raw/moon/MANIFEST.csv)
    "moon": {
        "moon_diviner_gcp.zip": ["diviner_gcp"],                     # ~2.7 GB raw (temperature, global)
        "moon_diviner_prp.zip": ["diviner_prp"],                     # ~0.6 GB raw (south pole)
        "moon_lola_ldem64.zip": ["lola_ldem64"],                     # ~0.5 GB raw (relief, global)
        "moon_south_pole_pgda.zip": ["pgda_south_pole"],             # ~0.35 GB raw
        "moon_other.zip": ["diviner_rocks", "lunar_prospector_grs", "usgs_geology", "lroc_pits"],
    },
    # Folders as written by scripts/download_earth.py (see src/analogs/catalog.py)
    "earth": {
        "earth_mask.zip": ["mcd12c1", "imerg_monthly"],                # ~2.3 GB raw (land cover + rain)
        "earth_relief.zip": ["srtmgl30", "etopo2022_30s"],             # ~1.9 GB raw
        "earth_temperature.zip": ["myd11c3"],                          # ~4.2 GB raw
        "earth_dust_snow.zip": ["merra2_dust", "mod10cm"],             # ~0.2 GB raw
        "earth_silica.zip": ["ecostress_wps"],                         # ~2.5 GB raw
    },
}
# "tables": the PROCESSED tables (a few hundred MB) — enough to run scripts/buscar.py without any raw data.
# Zip paths start with processed/ or interim/, and scripts/importar_datos.py puts them back in place.
TABLES = {"processed": "*.parquet", "interim": "*.npz"}


def pack_tables(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    target = out / "tables_processed.zip"
    files = [f for sub, pattern in TABLES.items() for f in sorted((DATA / sub).glob(pattern))]
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            z.write(f, f.relative_to(DATA).as_posix())
        if (DATA / "LEEME.md").exists():
            z.write(DATA / "LEEME.md", "LEEME.md")
    print(f"{target.name:32s} {len(files):3d} files → {target.stat().st_size / 1e6:8.1f} MB")


def pack(body: str, out: Path) -> None:
    if body == "tables":
        return pack_tables(out)
    out.mkdir(parents=True, exist_ok=True)
    for zip_name, folders in PACKS[body].items():
        target = out / zip_name
        missing = [f for f in folders if not (RAW / body / f).is_dir()]
        if missing:
            print(f"{zip_name:32s} skipped: missing folder(s) {missing} in {RAW / body}")
            continue
        files = [f for folder in folders for f in sorted((RAW / body / folder).rglob("*"))
                 if f.is_file() and not f.name.endswith(".part")]
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in files:
                z.write(f, f.relative_to(RAW).as_posix())
        raw_mb = sum(f.stat().st_size for f in files) / 1e6
        print(f"{zip_name:32s} {len(files):3d} files  {raw_mb:8.1f} MB → {target.stat().st_size / 1e6:8.1f} MB")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("body", choices=sorted(PACKS) + ["tables"])
    p.add_argument("--out", type=Path, required=True, help="folder for the zips (keep it outside OneDrive)")
    args = p.parse_args()
    pack(args.body, args.out)
