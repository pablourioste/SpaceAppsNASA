"""¿Qué datos hay en ESTE ordenador? Por cuerpo y dataset: ficheros, GB, qué falta del catálogo,
y las tablas ya procesadas (cuántas filas tiene cada una).

    .venv\\Scripts\\python.exe scripts\\inventario.py            # lo enseña en pantalla
    .venv\\Scripts\\python.exe scripts\\inventario.py --leeme    # y además escribe <DATA>/LEEME.md

El LEEME.md es docs/08_datos_LEEME.md (guía para personas y para Claude) + este inventario.
La lista de datasets sale del catálogo único: src/analogs/catalog.py.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analogs.catalog import DATASETS  # noqa: E402
from analogs.paths import DATA, INTERIM, PROCESSED, RAW  # noqa: E402

BODY_LABEL = {"earth": "🌍 Tierra", "moon": "🌕 Luna", "mars": "🔴 Marte"}
TEMPLATE = ROOT / "docs" / "08_datos_LEEME.md"


def folder_stats(p: Path) -> tuple[int, int]:
    files = [f for f in p.rglob("*") if f.is_file() and not f.name.startswith("partial_")]
    return len(files), sum(f.stat().st_size for f in files)


def gb(b: int) -> str:
    return f"{b / 1e9:.2f}" if b >= 1e7 else f"{b / 1e6:.1f} MB"


def build() -> tuple[str, list[str]]:
    """(texto markdown del inventario, líneas para la pantalla)."""
    md, screen = [], [f"Carpeta de datos: {DATA}", ""]
    md.append(f"Generado el {dt.datetime.now():%Y-%m-%d %H:%M} en `{DATA}`.\n")
    grand_n = grand_b = 0
    for body in ("earth", "moon", "mars"):
        rows = []
        known = {d.folder for d in DATASETS if d.body == body}
        on_disk = sorted(d.name for d in (RAW / body).iterdir() if d.is_dir()) if (RAW / body).exists() else []
        screen.append(f"=== raw/{body} ===")
        body_n = body_b = 0
        for d in [d for d in DATASETS if d.body == body]:
            p = RAW / body / d.folder
            n, b = folder_stats(p) if p.exists() else (0, 0)
            body_n += n
            body_b += b
            state = f"✅ {n} ficheros, {gb(b)} GB" if n else "❌ no está"
            rows.append(f"| `{d.folder}` | {d.product} | {d.what} | {d.variables} | {d.resolution} | {d.time} | "
                        f"{d.reading} | {d.download} | {state} |")
            screen.append(f"   {d.folder:24s} {'✅' if n else '❌'} {n:5d} ficheros {b / 1e9:7.2f} GB   {d.product}")
        for extra in sorted(set(on_disk) - known):
            n, b = folder_stats(RAW / body / extra)
            body_n += n
            body_b += b
            rows.append(f"| `{extra}` | (no está en el catálogo) | | | | | | | ⚠️ {n} ficheros, {gb(b)} GB |")
            screen.append(f"   {extra:24s} ⚠️ {n:5d} ficheros {b / 1e9:7.2f} GB   (no está en src/analogs/catalog.py)")
        grand_n += body_n
        grand_b += body_b
        screen.append(f"   {'TOTAL':24s}    {body_n:5d} ficheros {body_b / 1e9:7.2f} GB\n")
        md.append(f"### {BODY_LABEL[body]}: {body_n} ficheros, {body_b / 1e9:.2f} GB en `raw/{body}/`\n")
        md.append("| Carpeta | Producto | Qué es | Variables de la ficha | Resolución | Tiempo | Cómo se lee | Descarga | En este ordenador |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        md += rows
        md.append("")
    screen.append(f"TOTAL raw: {grand_n:,} ficheros, {grand_b / 1e9:.2f} GB\n")
    md.insert(1, f"**Total en `raw/`: {grand_n:,} ficheros, {grand_b / 1e9:.2f} GB.**\n")

    md.append("### Tablas procesadas\n")
    md.append("| Fichero | Filas | Columnas | Tamaño | Columnas que tiene |")
    md.append("|---|---|---|---|---|")
    screen.append("=== Tablas procesadas (lo que usan el buscador y la app) ===")
    for f in sorted(list(PROCESSED.glob("*.parquet")) + list(INTERIM.glob("*.parquet"))):
        df = pd.read_parquet(f)
        rel = f"{f.parent.name}/{f.name}"
        md.append(f"| `{rel}` | {len(df):,} | {df.shape[1]} | {f.stat().st_size / 1e6:.1f} MB | {', '.join(df.columns)} |")
        screen.append(f"   {rel:42s} {len(df):>10,} filas × {df.shape[1]:3d} col.  {f.stat().st_size / 1e6:7.1f} MB")
    for f in sorted(INTERIM.glob("*.npz")):
        rel = f"{f.parent.name}/{f.name}"
        md.append(f"| `{rel}` | (malla) | | {f.stat().st_size / 1e6:.1f} MB | |")
        screen.append(f"   {rel:42s} {'(malla)':>10s}                {f.stat().st_size / 1e6:7.1f} MB")
    return "\n".join(md), screen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leeme", action="store_true", help="escribe también <DATA>/LEEME.md")
    args = ap.parse_args()
    md, screen = build()
    print("\n".join(screen))
    if args.leeme:
        text = TEMPLATE.read_text(encoding="utf-8").replace("<!-- INVENTARIO -->", md)
        (DATA / "LEEME.md").write_text(text, encoding="utf-8")
        print(f"\nEscrito: {DATA / 'LEEME.md'}")


if __name__ == "__main__":
    main()
