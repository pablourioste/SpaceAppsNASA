"""Descarga el KIT DE DATOS DE LA LUNA (v1) → data/raw/moon/<dataset>/

    python scripts/download_moon.py            # descarga lo que falte (se puede relanzar: reanuda)
    python scripts/download_moon.py --list     # solo enseña qué bajaría

Qué se baja y por qué: docs/06_datos_luna.md. Criterios: (1) da una variable de la ficha,
(2) entre todos cubren TODA la Luna (zona global ±60° + zona polar), (3) resumen de todo el
periodo (no una fecha), (4) resolución de ~1 km o la que haya, sin pasarse de peso,
(5) fuente oficial (NASA PDS, NASA Goddard PGDA, USGS, LROC).

Solo usa la librería estándar de Python y `curl` (incluido en Windows 10+, Mac y Linux).
Al acabar escribe data/raw/moon/MANIFEST.csv: qué fichero, de qué URL, cuántos bytes y cuándo.
"""
import argparse
import csv
import datetime as dt
import html
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consolas de Windows (cp1252)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analogs.paths import RAW  # noqa: E402  (misma carpeta de datos que el resto: ver paths.py)

DEST = RAW / "moon"

PDS = "https://pds-geosciences.wustl.edu"
DIV = f"{PDS}/lro/urn-nasa-pds-lro_diviner_derived1"
PGDA = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp"


def with_labels(url_base: str, exts=(".lbl", ".xml")) -> list[str]:
    """El fichero de datos + sus etiquetas (las etiquetas dicen cómo leerlo)."""
    stem = url_base.rsplit(".", 1)[0]
    return [url_base] + [stem + e for e in exts]


GCP_BANDS = [f"{a:02d}n{a + 10:02d}n" for a in range(0, 90, 10)] + [f"{a + 10:02d}s{a:02d}s" for a in range(0, 90, 10)]

# dataset → lista de URLs, por ORDEN DE PRIORIDAD (primero lo del polo sur y lo pequeño)
DATASETS: dict[str, list[str]] = {
    # Temperatura media/máx y profundidad del hielo, polo sur (~0,5 km). 605 MB
    "diviner_prp": with_labels(f"{DIV}/data_derived_prp/dlre_prp_south.tab"),
    # Pendiente, rugosidad (escalas 100–1600 m) y exponente de Hurst, 80–90°S, 1 km. ~1,5 MB c/u
    "pgda_south_pole": [f"{PGDA}/LDRM_80S_1000MPP_ADJ_{v}_{L}M.TIF"
                        for v in ("SLP", "ROUGH", "RMSD") for L in (100, 200, 400, 800, 1600)]
                       + [f"{PGDA}/LPSR_80S_20MPP_ADJ.TIF",      # sombra permanente, 20 m. 148 MB
                          f"{PGDA}/LDEM_80S_80MPP_ADJ.TIF"],     # relieve, 80 m. 181 MB
    # Composición química (FeO, Al2O3, TiO2…) de TODA la Luna, 2° y 5°. ~12 MB
    "lunar_prospector_grs": with_labels(f"{PDS}/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_2deg.tab")
                            + with_labels(f"{PDS}/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_high1_elem_abundance_5deg.tab")
                            + [f"{PDS}/lunar/lp-l-grs-5-elem-abundance-v1/lp_9001/data/lpgrs_elem_abundance.fmt"],
    # Abundancia de rocas, 60°N–60°S, ~950 m. 88,5 MB
    "diviner_rocks": with_labels(f"{DIV}/data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.img"),
    # Relieve global de LOLA, 64 px/° (~470 m) → pendiente y rugosidad fuera del polo. 531 MB
    "lola_ldem64": with_labels(f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_64.img", (".lbl",)),
    # Mapa geológico unificado (detalle para las fichas finales). 224 MB
    "usgs_geology": ["https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip"],
    # Temperatura de TODA la Luna por casilla de 0,5° y hora local: 18 bandas de 10°. 156 MB c/u (~2,8 GB)
    "diviner_gcp": [u for b in GCP_BANDS for u in with_labels(f"{DIV}/data_derived_gcp/global_cumul_avg_cyl_{b}_002.tab")],
}

# EXTRAS: no dan ninguna variable de la ficha. Solo con --extras (revisión 14/11: se quitaron del kit)
EXTRAS: dict[str, list[str]] = {
    # Radar CPR de toda la Luna, ~950 m. 265 MB. Solo si se sigue el eje "radar" (enfoque §4)
    "minirf_cpr": with_labels(f"{PDS}/lro/lro-l-mrflro-5-global-mosaic-v1/lromrf_1001/data/32ppd/global_cpr_32ppd_simp_0c.img"),
    # Exponente de Hurst (cómo cambia la rugosidad con la escala), 80–90°S. 1,4 MB
    "pgda_south_pole": [f"{PGDA}/LDRM_80S_1000MPP_ADJ_H.TIF"],
}

LROC_PITS_URL = "https://lroc.im-ldi.com/atlases/pits/list"


def remote_size(url: str) -> int | None:
    r = subprocess.run(["curl", "-sSIL", "--max-time", "60", url], capture_output=True, text=True)
    sizes = re.findall(r"(?im)^content-length:\s*(\d+)", r.stdout)
    return int(sizes[-1]) if sizes else None


def fetch(dataset: str, url: str) -> dict:
    out = DEST / dataset / url.rsplit("/", 1)[1]
    out.parent.mkdir(parents=True, exist_ok=True)
    size = remote_size(url)
    if out.exists() and size is not None and out.stat().st_size == size:
        return {"dataset": dataset, "file": out.name, "url": url, "bytes": size, "status": "ya estaba"}
    part = out.with_suffix(out.suffix + ".part")
    cmd = ["curl", "-sSL", "--fail", "--retry", "5", "--retry-delay", "5", "-C", "-", "-o", str(part), url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not part.exists():
        return {"dataset": dataset, "file": out.name, "url": url, "bytes": 0,
                "status": f"ERROR curl {r.returncode}: {r.stderr.strip()[:120]}"}
    part.replace(out)
    got = out.stat().st_size
    ok = size is None or got == size
    return {"dataset": dataset, "file": out.name, "url": url, "bytes": got,
            "status": "ok" if ok else f"ERROR tamaño {got} ≠ {size}"}


def fetch_lroc_pits() -> dict:
    """La lista de pozos es una tabla web: se guarda como CSV."""
    out = DEST / "lroc_pits" / "lroc_pits_list.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["curl", "-sSL", "--fail", "--max-time", "120", LROC_PITS_URL], capture_output=True)
    page = r.stdout.decode("utf-8", "ignore")
    page = re.sub(r"(?is)<(script|style).*?</\1>", "", page)
    clean = lambda c: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
    rows = [[clean(c) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
            for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page)]
    rows = [r for r in rows if r]
    with open(out, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    n = max(len(rows) - 1, 0)
    return {"dataset": "lroc_pits", "file": out.name, "url": LROC_PITS_URL, "bytes": out.stat().st_size,
            "status": f"ok ({n} pozos)" if n > 200 else f"ERROR: solo {n} filas"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="solo enseñar qué se bajaría")
    ap.add_argument("--workers", type=int, default=4, help="descargas en paralelo")
    ap.add_argument("--extras", action="store_true", help="bajar también los EXTRAS (radar Mini-RF, Hurst)")
    args = ap.parse_args()

    jobs = [(d, u) for d, urls in DATASETS.items() for u in urls]
    if args.extras:
        jobs += [(d, u) for d, urls in EXTRAS.items() for u in urls]
    if args.list:
        for d, u in jobs:
            print(f"{d:22s} {u}")
        print(f"{len(jobs)} ficheros + lista de pozos de LROC → {DEST}")
        return

    print(f"Destino: {DEST}\n{len(jobs)} ficheros + lista de pozos de LROC", flush=True)
    results = [fetch_lroc_pits()]
    print(f"[{results[0]['status']}] lroc_pits/{results[0]['file']}", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch, d, u) for d, u in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            results.append(r)
            print(f"[{i:3d}/{len(jobs)}] [{r['status']}] {r['dataset']}/{r['file']} "
                  f"({r['bytes'] / 1e6:.1f} MB)", flush=True)

    now = dt.datetime.now().isoformat(timespec="seconds")
    with open(DEST / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dataset", "file", "url", "bytes", "status", "downloaded"])
        w.writeheader()
        for r in sorted(results, key=lambda r: (r["dataset"], r["file"])):
            w.writerow({**r, "downloaded": now})
    errors = [r for r in results if r["status"].startswith("ERROR")]
    total = sum(r["bytes"] for r in results) / 1e9
    print(f"\nFIN: {len(results) - len(errors)} ok, {len(errors)} con error, {total:.2f} GB en {DEST}")
    for r in errors:
        print(f"  ✗ {r['dataset']}/{r['file']}: {r['status']}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
