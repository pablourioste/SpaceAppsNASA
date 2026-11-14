"""Extract the variables at every Mars target site (ROADMAP task 3.5).

    python scripts/download_data.py mola tes grs grs_elements tes_atmos   # once
    python scripts/build_mars_features.py

Writes data/processed/fichas_objetivos_mars.parquet and outputs/validation/mars_sites_features.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from analogs.mars import build_mars_targets  # noqa: E402
from analogs.paths import VALIDATION  # noqa: E402


def main() -> None:
    df = build_mars_targets()
    show = ["name", "lat", "lon", "elevation_m", "slope_deg", "roughness_deg", "thermal_inertia_day_SI",
            "grs_h2o_wt_pct", "grs_cl_wt_pct", "t_mean_K", "t_max_K", "dust_aod", "p_surf_Pa"]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(df[show].round(2).to_string(index=False))
    print(f"\n{len(df)} Mars sites → {VALIDATION / 'mars_sites_features.csv'}")


if __name__ == "__main__":
    main()
