"""Build the Moon card grid (whole Moon, H3 res 4) and the Moon target-site cards (ROADMAP 3.7).

    python scripts/download_moon.py      # once
    python scripts/build_moon_grid.py

Writes:
    data/processed/luna_h3r4.parquet            one row per hexagon (288,122), every variable  → Drive
    data/processed/luna_h3r4_columnas.csv       unit, source and method of every column          → git
    data/processed/fichas_objetivos_moon.csv    the Moon target sites (card of their hexagon)     → git
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

from analogs.moon import build_moon_grid, build_moon_targets  # noqa: E402

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:6.0f} s] {msg}", flush=True)


def main() -> None:
    grid = build_moon_grid(log)
    sites = build_moon_targets(grid)
    log(f"done: {len(grid):,} hexagons, {len(sites)} target sites")

    show = ["name", "slope_deg", "roughness_deg", "lola_measured_frac", "t_mean_K", "t_max_K", "t_min_K",
            "feo_wt_pct", "rock_abundance_pct", "ice_frac_1m", "psr_frac", "pit_dist_km"]
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        print(sites[show].round(2).to_string(index=False))
    print("\nCoverage (non-empty hexagons):")
    for col in ["slope_deg", "t_mean_K", "t_max_K", "feo_wt_pct", "rock_abundance_pct", "ice_frac_1m", "psr_frac"]:
        print(f"  {col:20s} {grid[col].notna().mean() * 100:5.1f} %")


if __name__ == "__main__":
    main()
