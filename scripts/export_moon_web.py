"""Export the Moon card grid for the web app (ROADMAP 3.16, Moon part). Same as export_mars_web.py.

    python scripts/build_moon_grid.py     # first, once (~3 min)
    python scripts/export_moon_web.py     # ~1 min

Reads data/processed/luna_h3r4.parquet and fichas_objetivos_moon.parquet and writes app/data/luna/
(index.json + one compressed binary per H3 region + objetivos.json with the real cards of the Moon
target sites). Format: docs/07_card_grid_binary_format.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

from analogs.config import load_variables  # noqa: E402
from analogs.export import (MOON_DISPLAY, MOON_SOURCES, MOON_WEB_COLUMNS,  # noqa: E402
                            write_body_targets, write_grid_binary)
from analogs.moon import H3_RES  # noqa: E402
from analogs.paths import APP_DATA, PROCESSED  # noqa: E402

CELL_SIZE_KM = {4: 12.3, 5: 4.7}   # flat-to-flat size of an average H3 hexagon on the Moon


def main() -> None:
    df = pd.read_parquet(PROCESSED / f"luna_h3r{H3_RES}.parquet", columns=["h3", *MOON_WEB_COLUMNS])
    index = write_grid_binary(df, "luna", MOON_WEB_COLUMNS, MOON_SOURCES, MOON_DISPLAY,
                              extra={"cell_size_km": CELL_SIZE_KM[H3_RES]})
    sizes = [r["bytes"] for r in index["regions"].values()]
    print(f"app/data/luna/: {len(sizes)} regions, {index['n_cells']:,} cells, "
          f"{sum(sizes) / 1e6:.2f} MB total, {min(sizes) / 1e3:.0f}–{max(sizes) / 1e3:.0f} KB per region")
    write_body_targets(pd.read_parquet(PROCESSED / "fichas_objetivos_moon.parquet"), "luna",
                       MOON_WEB_COLUMNS, load_variables())
    print(f"{APP_DATA / 'luna' / 'objetivos.json'}: real cards of the Moon target sites")


if __name__ == "__main__":
    main()
