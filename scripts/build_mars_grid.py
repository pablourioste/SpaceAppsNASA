"""Build the Mars card grid on H3 resolution 5 (ROADMAP task 3.5, decision 007).

    python scripts/build_mars_grid.py                 # whole planet (~20–30 min)
    python scripts/build_mars_grid.py --tiles 44n000  # quick test on one MOLA tile, no poles

Needs the Mars kit in data/raw/mars/ (python scripts/download_data.py).
Writes data/processed/mars_h3r5.parquet and data/processed/fichas_objetivos_mars.parquet.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analogs.mars_grid import build_mars_grid, build_mars_targets  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", nargs="*", help="only these MOLA 128 ppd tiles (e.g. 44n000)")
    args = ap.parse_args()
    df = build_mars_grid(tiles=args.tiles or None, with_poles=not args.tiles)
    sites = build_mars_targets(df)
    cols = ["name", "h3", "slope_deg", "roughness_deg", "mola_measured_frac", "thermal_inertia_day_SI",
            "ice_depth_m", "grs_h2o_wt_pct", "t_mean_K", "t_max_K", "dust_aod", "sun_elev_max_deg"]
    print(sites[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
