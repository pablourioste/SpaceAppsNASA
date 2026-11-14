"""Hace la LISTA de los datos que tienes en una carpeta (para comparar con un compañero).

    python scripts/list_data.py data/raw/moon --nombre marc

Escribe data/raw/moon/LISTADO_marc.csv con: ruta relativa, bytes y huella SHA-256 de cada fichero.
Esa lista SÍ va a git (los datos no). Si dos personas tienen el mismo fichero, la huella es idéntica.
Solo usa la librería estándar de Python.
"""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consolas de Windows (cp1252)


def sha256(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--nombre", required=True, help="tu nombre, para el fichero LISTADO_<nombre>.csv")
    args = ap.parse_args()

    files = sorted(p for p in args.carpeta.rglob("*")
                   if p.is_file() and not p.name.startswith(("LISTADO_", "MANIFEST", ".gitkeep"))
                   and not p.name.endswith(".part"))
    out = args.carpeta / f"LISTADO_{args.nombre}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ruta", "bytes", "sha256"])
        for i, p in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {p.relative_to(args.carpeta)}", flush=True)
            w.writerow([p.relative_to(args.carpeta).as_posix(), p.stat().st_size, sha256(p)])
    total = sum(p.stat().st_size for p in files) / 1e9
    print(f"\n{len(files)} ficheros, {total:.2f} GB → {out}")


if __name__ == "__main__":
    main()
