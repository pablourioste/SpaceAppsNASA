"""Copia los datos de un PENDRIVE (zip o carpeta) al sitio correcto de este ordenador.

    .venv\\Scripts\\python.exe scripts\\importar_datos.py E:\\datos.zip --dry-run   # solo enseña qué haría
    .venv\\Scripts\\python.exe scripts\\importar_datos.py E:\\datos.zip
    .venv\\Scripts\\python.exe scripts\\importar_datos.py E:\\carpeta_con_zips      # todos los .zip de la carpeta
    .venv\\Scripts\\python.exe scripts\\importar_datos.py E:\\carpeta_sin_zips      # copia la carpeta tal cual

Destino: <DATA>/raw/<moon|mars|earth>/<dataset>/…   (DATA: ver src/analogs/paths.py; fuera de git y de OneDrive)

Cómo decide dónde va cada fichero (por la ruta dentro del zip o carpeta):
  1. Si la ruta contiene una carpeta moon / mars / earth (o luna / marte / tierra) → lo que va detrás
     se copia tal cual dentro de raw/<cuerpo>/. Funciona con zips que empiezan por raw/, data/raw/, etc.
     (es el formato de los zips de scripts/pack_data.py: mars/mola_megdr_16ppd/…)
  2. Si no, pero contiene una carpeta de dataset conocida (p. ej. lola_ldem64, mola_megdr_16ppd) →
     raw/<su cuerpo>/<dataset>/…
  3. Si no, va a raw/_sin_clasificar/ y se avisa.
Los ficheros que ya existen con el mismo tamaño no se vuelven a copiar (se puede relanzar).
"""
import argparse
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analogs.catalog import BODY_ALIASES, known_folders  # noqa: E402
from analogs.paths import DATA, RAW  # noqa: E402

DATASET_BODY = known_folders()            # carpeta → cuerpo, del catálogo único (src/analogs/catalog.py)
SKIP = {"__MACOSX", ".DS_Store", "Thumbs.db", "desktop.ini"}


def destination(rel: PurePosixPath) -> tuple[str, Path]:
    parts = [p for p in rel.parts if p not in ("", ".")]
    if parts == ["LEEME.md"]:
        return "tablas", DATA / "LEEME.md"
    for k, p in enumerate(parts[:-1]):              # tablas ya procesadas (pack_data.py tables)
        if p.lower() in ("processed", "interim"):
            return "tablas", DATA / p.lower() / Path(*parts[k + 1:])
    for k, p in enumerate(parts[:-1]):
        if p.lower() in BODY_ALIASES:
            body = BODY_ALIASES[p.lower()]
            return body, RAW / body / Path(*parts[k + 1:])
    for k, p in enumerate(parts[:-1]):
        if p.lower() in DATASET_BODY:
            body = DATASET_BODY[p.lower()]
            return body, RAW / body / Path(*parts[k:])
    return "_sin_clasificar", RAW / "_sin_clasificar" / Path(*parts)


def entries(src: Path):
    """(ruta relativa, tamaño, función que abre el fichero) de cada fichero del zip o carpeta."""
    if src.is_file() and zipfile.is_zipfile(src):
        z = zipfile.ZipFile(src)
        for info in z.infolist():
            if info.is_dir() or any(s in info.filename for s in SKIP):
                continue
            yield PurePosixPath(info.filename), info.file_size, (lambda i=info: z.open(i))
    elif src.is_dir() and list(src.glob("*.zip")):          # carpeta con zips (p. ej. los de pack_data.py)
        for zp in sorted(src.glob("*.zip")):
            print(f"  · {zp.name}")
            yield from entries(zp)
    elif src.is_dir():
        for f in src.rglob("*"):
            if f.is_file() and f.name not in SKIP:
                yield PurePosixPath(f.relative_to(src).as_posix()), f.stat().st_size, (lambda f=f: f.open("rb"))
    else:
        raise SystemExit(f"{src} no es un .zip ni una carpeta. (Para .7z o .rar: descomprímelo primero y pasa la carpeta)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("origen", type=Path, help="zip o carpeta del pendrive")
    ap.add_argument("--dry-run", action="store_true", help="solo enseña qué copiaría")
    args = ap.parse_args()

    print(f"Destino: {RAW}\n")
    stats: dict[str, list[int]] = {}
    datasets: dict[str, set] = {}
    for rel, size, opener in entries(args.origen):
        body, dest = destination(rel)
        st = stats.setdefault(body, [0, 0, 0])
        st[0] += 1
        st[1] += size
        rel_dest = dest.relative_to(DATA if body == "tablas" else RAW / body)
        if len(rel_dest.parts) > 1:
            datasets.setdefault(body, set()).add(rel_dest.parts[0])
        if dest.exists() and dest.stat().st_size == size:
            st[2] += 1
            continue
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with opener() as fin, open(dest, "wb") as fout:
                shutil.copyfileobj(fin, fout, 16 << 20)

    print(f"{'cuerpo':16s} {'ficheros':>9s} {'GB':>8s} {'ya estaban':>11s}   carpetas")
    for body, (n, size, skipped) in sorted(stats.items()):
        print(f"{body:16s} {n:9,} {size / 1e9:8.2f} {skipped:11,}   {', '.join(sorted(datasets.get(body, [])))}")
    if "_sin_clasificar" in stats:
        print(f"\n⚠️  Hay ficheros sin clasificar en {RAW / '_sin_clasificar'}: muévelos a mano a raw/<cuerpo>/<dataset>/")
    print("\n(dry-run: no se ha copiado nada)" if args.dry_run
          else "\nHecho. Comprueba con: .venv\\Scripts\\python.exe scripts\\inventario.py --leeme")


if __name__ == "__main__":
    main()
