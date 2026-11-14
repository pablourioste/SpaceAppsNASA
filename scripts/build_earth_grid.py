"""Malla de fichas de la Tierra en H3 + binario para la web (equivalente a build_mars_grid.py +
export_mars_web.py de Marte).

    .venv\\Scripts\\python.exe scripts\\build_earth_grid.py               # res 6 (~6,5 km, la más parecida a Marte)
    .venv\\Scripts\\python.exe scripts\\build_earth_grid.py --res 5       # res 5 (~17 km, 7 veces menos celdas)
    .venv\\Scripts\\python.exe scripts\\build_earth_grid.py --no-web      # solo el parquet

Antes: download_earth.py (datos) y build_earth_mask.py (máscara).
Escribe:
  <DATA>/processed/earth_h3r<res>.parquet    una fila por celda H3 de todo el planeta (mar = NaN)
  app/data/tierra/index.json + rNNN.bin.gz    formato binario de docs/07_card_grid_binary_format.md
y comprueba el binario con scripts/check_grid_binary.py.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from analogs.earth_grid import EARTH_WEB_COLUMNS, build_earth_grid, earth_sources  # noqa: E402
from analogs.export import write_grid_binary  # noqa: E402
from analogs.paths import APP_DATA, PROCESSED  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=6, help="resolución H3 (6 ≈ 6,5 km; 5 ≈ 17 km)")
    ap.add_argument("--no-web", action="store_true", help="no escribir app/data/tierra/")
    args = ap.parse_args()

    df, relief_source = build_earth_grid(args.res)
    land = df[df.land_frac > 0]
    print(f"\nCeldas: {len(df):,} en total · {len(land):,} con tierra · {int((land.in_mask == 1).sum()):,} en la máscara")
    print(land.drop(columns=["h3"]).describe(percentiles=[.05, .5, .95]).T[["count", "min", "5%", "50%", "95%", "max"]]
          .round(2).to_string())
    if args.no_web:
        return
    index = write_grid_binary(df, "tierra", EARTH_WEB_COLUMNS, earth_sources(relief_source))
    total = sum(r["bytes"] for r in index["regions"].values())
    print(f"\napp/data/tierra/: {len(index['regions'])} regiones, {total / 1e6:.1f} MB "
          f"(media {total / len(index['regions']) / 1e3:.0f} KB por región) → {APP_DATA / 'tierra'}")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_grid_binary.py"), "tierra",
                    str(PROCESSED / f"earth_h3r{args.res}.parquet")], check=False)


if __name__ == "__main__":
    main()
