"""Descarga los datos de la TIERRA → <DATA>/raw/earth/<carpeta>/   (carpetas: src/analogs/catalog.py)

    .venv\\Scripts\\python.exe scripts\\download_earth.py                 # todo lo que falte
    .venv\\Scripts\\python.exe scripts\\download_earth.py mask temp       # solo algunos grupos
    .venv\\Scripts\\python.exe scripts\\download_earth.py --list          # enseña qué bajaría

Grupos: mask (cubierta del suelo + lluvia) · dem (relieve 30″) · dem15 (relieve 15″ ≈ 460 m, como Marte/Luna)
        · temp (temperatura) · polvo · silice · nieve
Se puede relanzar: lo que ya está descargado se salta.

Necesita una cuenta de Earthdata Login en ~/.netrc (Windows: C:\\Users\\<tú>\\.netrc):
    machine urs.earthdata.nasa.gov login <usuario> password <contraseña>
y haber autorizado en https://urs.earthdata.nasa.gov → Applications la app "NASA GESDISC DATA ARCHIVE".
ETOPO 2022 (NOAA) no pide cuenta. Cada fichero bajado se apunta en raw/earth/MANIFEST.csv.
"""
import argparse
import csv
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:  # certificados del sistema (antivirus / proxies en Windows)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# earthaccess busca _netrc en Windows; si solo existe .netrc, se lo indicamos
if "NETRC" not in os.environ:
    for name in (".netrc", "_netrc"):
        if (Path.home() / name).exists():
            os.environ["NETRC"] = str(Path.home() / name)
            break

import earthaccess  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analogs.paths import RAW  # noqa: E402

DEST = RAW / "earth"
CLIMA = ("2019-01-01", "2023-12-31")      # periodo de clima: 5 años completos

# grupo → carpeta → cómo se descarga
#   earthaccess: búsqueda normal en Earthdata y descarga del fichero entero
#   opendap:     solo unas variables del fichero (servicio OPeNDAP de Earthdata) → MB en vez de GB
#   url:         descarga directa de una URL pública
GROUPS: dict[str, dict[str, dict]] = {
    "mask": {
        "mcd12c1": dict(how="earthaccess", short_name="MCD12C1", version="061", temporal=("2025-01-01", "2025-12-31")),
        "imerg_monthly": dict(how="earthaccess", short_name="GPM_3IMERGM", version="07", temporal=CLIMA),
    },
    "dem": {
        "srtmgl30": dict(how="earthaccess", short_name="SRTMGL30", version="002"),
        "etopo2022_30s": dict(how="url", urls=[
            "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/30s/30s_surface_elev_gtif/"
            "ETOPO_2022_v1_30s_N90W180_surface.tif"]),
    },
    # Relieve a 15″ (~460 m): MISMA línea base que Marte (MOLA 128 px/°, ~463 m) y la Luna (LOLA ldem_64,
    # ~474 m) para la pendiente y la rugosidad (decisión 006 / ROADMAP 3.5). Piezas de 15°×15°: solo las
    # que tienen tierra (según la máscara MCD12C1). ~20–35 MB cada una.
    "dem15": {
        "etopo2022_15s": dict(how="etopo15"),
    },
    "temp": {
        "myd11c3": dict(how="earthaccess", short_name="MYD11C3", version="061", temporal=CLIMA),
    },
    "polvo": {
        "merra2_dust": dict(how="opendap", short_name="M2TMNXAER", version="5.12.4", temporal=CLIMA,
                            variables=["DUEXTTAU", "TOTEXTTAU", "lat", "lon"]),
    },
    "silice": {
        "ecostress_wps": dict(how="earthaccess", short_name="ECO_L3G_WPS", version="001"),
    },
    "nieve": {
        "mod10cm": dict(how="earthaccess", short_name="MOD10CM", version="61", temporal=CLIMA),
    },
}


_LOCK = __import__("threading").Lock()


def _manifest(rows: list[list]) -> None:
    with _LOCK:            # varias descargas en paralelo escriben aquí
        _manifest_unlocked(rows)


def _manifest_unlocked(rows: list[list]) -> None:
    """Añade/actualiza filas de MANIFEST.csv (una por dataset + fichero; relanzar no duplica)."""
    path = DEST / "MANIFEST.csv"
    header = ["dataset", "product", "file", "bytes", "downloaded_utc"]
    table: dict[tuple, list] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in list(csv.reader(fh))[1:]:
                table[(r[0], r[2])] = r
    for r in rows:
        key = (r[0], r[2])
        if key not in table or str(table[key][3]) != str(r[3]):   # nuevo o con otro tamaño
            table[key] = [str(x) for x in r]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(sorted(table.values()))


def _row(folder: str, product: str, p: Path) -> list:
    return [folder, product, p.name, p.stat().st_size, dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")]


def get_earthaccess(folder: str, spec: dict, listing: bool, threads: int) -> None:
    params = {k: spec[k] for k in ("short_name", "version", "temporal") if k in spec}
    results = earthaccess.search_data(**params)
    size = sum((r.size() if callable(r.size) else r.size) or 0 for r in results)
    print(f"  {folder}: {len(results)} ficheros, {size:,.0f} MB  ({spec['short_name']} v{spec['version']})")
    if listing or not results:
        return
    out = DEST / folder
    out.mkdir(parents=True, exist_ok=True)
    files = [Path(f) for f in earthaccess.download(results, local_path=str(out), threads=threads)]
    for partial in out.glob("partial_*"):
        partial.unlink(missing_ok=True)
    _manifest([_row(folder, spec["short_name"], f) for f in files if f.exists()])


def get_opendap(folder: str, spec: dict, listing: bool) -> None:
    results = earthaccess.search_data(short_name=spec["short_name"], version=spec["version"], temporal=spec["temporal"])
    print(f"  {folder}: {len(results)} ficheros, solo {', '.join(spec['variables'])}  ({spec['short_name']}, OPeNDAP)")
    if listing:
        return
    out = DEST / folder
    out.mkdir(parents=True, exist_ok=True)
    session = earthaccess.get_requests_https_session()
    ce = ";".join(f"/{v}" for v in spec["variables"])
    rows = []
    for g in results:
        cid, gur = g["meta"]["collection-concept-id"], g["umm"]["GranuleUR"]
        target = out / (gur.split(":")[-1].replace(".nc4", "") + "_subset.nc4")
        if target.exists() and target.stat().st_size > 0:
            continue
        url = f"https://opendap.earthdata.nasa.gov/collections/{cid}/granules/{gur}.dap.nc4?dap4.ce={ce}"
        r = session.get(url, timeout=300)
        r.raise_for_status()
        if not r.content.startswith(b"\x89HDF"):
            raise RuntimeError(f"Respuesta inesperada para {gur}: {r.content[:80]!r}")
        target.write_bytes(r.content)
        rows.append(_row(folder, spec["short_name"], target))
        print(f"    {target.name}  {len(r.content) / 1e6:.1f} MB")
    _manifest(rows)


def get_url(folder: str, spec: dict, listing: bool, quiet: bool = False) -> None:
    if not quiet:
        print(f"  {folder}: {len(spec['urls'])} fichero(s) por URL directa")
    if listing:
        return
    out = DEST / folder
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for url in spec["urls"]:
        target = out / url.rsplit("/", 1)[1]
        part = target.with_name(target.name + ".part")
        if target.exists() and not part.exists():
            continue
        # curl reanuda (-C -) si se cortó; viene con Windows 10+, Mac y Linux. Se baja a .part y se renombra al acabar
        subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "5", "-o", str(part), url], check=True)
        part.replace(target)
        rows.append(_row(folder, "url", target))
    _manifest(rows)


ETOPO15 = "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/15s/15s_surface_elev_gtif/"


def etopo15_tiles() -> list[str]:
    """Nombres de las piezas ETOPO 2022 15″ (15°×15°, nombre = esquina superior izquierda) con tierra."""
    import numpy as np

    from analogs.paths import INTERIM
    npz = INTERIM / "earth_mask_005deg.npz"
    land = np.load(npz)["land"] if npz.exists() else None
    names = []
    for top in range(90, -90, -15):
        for west in range(-180, 180, 15):
            if land is not None:
                r0, c0 = int((90 - top) / 0.05), int((west + 180) / 0.05)
                if not land[r0:r0 + 300, c0:c0 + 300].any():
                    continue
            ns, ew = ("N" if top >= 0 else "S"), ("E" if west >= 0 else "W")
            names.append(f"ETOPO_2022_v1_15s_{ns}{abs(top):02d}{ew}{abs(west):03d}_surface.tif")
    return names


def get_etopo15(folder: str, listing: bool, threads: int) -> None:
    from concurrent.futures import ThreadPoolExecutor

    names = etopo15_tiles()
    print(f"  {folder}: {len(names)} piezas con tierra (~20–35 MB c/u)")
    if listing:
        return
    spec = {"urls": [ETOPO15 + n for n in names]}
    out = DEST / folder
    out.mkdir(parents=True, exist_ok=True)

    def one(url: str) -> None:
        for _ in range(5):
            try:
                get_url(folder, {"urls": [url]}, False, quiet=True)
                return
            except subprocess.CalledProcessError:
                continue
        print(f"    ✗ {url.rsplit('/', 1)[1]} (relanza para reintentar)")

    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(one, spec["urls"]))
    print(f"    {len(list(out.glob('*.tif')))} piezas en {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("groups", nargs="*", default=list(GROUPS), help=f"grupos: {', '.join(GROUPS)}")
    ap.add_argument("--list", action="store_true", help="solo enseña qué bajaría")
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()

    earthaccess.login(strategy="netrc")
    DEST.mkdir(parents=True, exist_ok=True)
    for g in args.groups:
        print(f"[{g}]")
        for folder, spec in GROUPS[g].items():
            {"earthaccess": lambda: get_earthaccess(folder, spec, args.list, args.threads),
             "opendap": lambda: get_opendap(folder, spec, args.list),
             "url": lambda: get_url(folder, spec, args.list),
             "etopo15": lambda: get_etopo15(folder, args.list, args.threads)}[spec["how"]]()
    print(f"\nDestino: {DEST}")


if __name__ == "__main__":
    main()
