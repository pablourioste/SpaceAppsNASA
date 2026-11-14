"""Fichas de la Tierra con todas las variables disponibles, a dos resoluciones:

    .venv\\Scripts\\python.exe scripts\\build_earth_mask.py        # antes (una vez)
    .venv\\Scripts\\python.exe scripts\\build_earth_features.py

Salida (data/processed/):
  fichas_tierra_005deg.parquet   una fila por PÍXEL de 0,05° (~5,6 km): la más fina, para buscar
  fichas_tierra_h3r5.parquet     una fila por hexágono H3 res 5 (~17 km): más ligera, para la app
Usa lo que haya descargado: si falta un producto, su columna queda vacía y se avisa.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analogs.earth import build_earth_cells, build_earth_pixels, compute_fields, load_mask  # noqa: E402
from analogs.paths import PROCESSED  # noqa: E402


def report(df, name: str, unit: str) -> None:
    print(f"\n{PROCESSED / name}: {len(df):,} {unit}, {int(df.in_mask.sum()):,} dentro de la máscara")
    num = df.select_dtypes("number").drop(columns=["env", "pixel"], errors="ignore")
    print(num.describe(percentiles=[0.05, 0.5, 0.95]).T[["count", "min", "5%", "50%", "95%", "max"]].round(1).to_string())


if __name__ == "__main__":
    m = load_mask()
    fields = compute_fields(m)
    report(build_earth_pixels(fields, m), "fichas_tierra_005deg.parquet", "píxeles de 0,05°")
    report(build_earth_cells(fields, m), "fichas_tierra_h3r5.parquet", "hexágonos H3 res 5")
