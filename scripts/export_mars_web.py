"""Export the Mars card grid for the web app (ROADMAP 3.16, Mars part).

    python scripts/build_mars_grid.py     # first, once (~18 min)
    python scripts/export_mars_web.py     # ~1 min

Reads data/processed/mars_h3r5.parquet and fichas_objetivos_mars.parquet and writes
app/data/marte/ (index.json + one compressed binary per H3 region + objetivos.json with the
real cards of the Mars target sites). Format: docs/07_card_grid_binary_format.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from analogs.config import load_variables  # noqa: E402
from analogs.export import MARS_SOURCES, MARS_WEB_COLUMNS, write_grid_binary, write_mars_targets  # noqa: E402
from analogs.paths import APP_DATA, PROCESSED  # noqa: E402


def main() -> None:
    df = pd.read_parquet(PROCESSED / "mars_h3r5.parquet", columns=["h3", *MARS_WEB_COLUMNS])
    index = write_grid_binary(df, "marte", MARS_WEB_COLUMNS, MARS_SOURCES)
    sizes = [r["bytes"] for r in index["regions"].values()]
    print(f"app/data/marte/: {len(sizes)} regions, {index['n_cells']:,} cells, "
          f"{sum(sizes) / 1e6:.1f} MB total, {min(sizes) / 1e3:.0f}–{max(sizes) / 1e3:.0f} KB per region")
    write_mars_targets(pd.read_parquet(PROCESSED / "fichas_objetivos_mars.parquet"), load_variables())
    print(f"{APP_DATA / 'marte' / 'objetivos.json'}: real cards of the Mars target sites")


if __name__ == "__main__":
    main()
