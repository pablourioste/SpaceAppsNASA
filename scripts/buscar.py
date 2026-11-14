"""Buscador en la terminal: escribe unas condiciones y te dice qué sitios de la Tierra se parecen más.

    .venv\\Scripts\\python.exe scripts\\buscar.py                  # píxeles de 0,05° (~5,6 km), lo más fino
    .venv\\Scripts\\python.exe scripts\\buscar.py --malla h3r5     # hexágonos de ~17 km, más rápido

Sirve para comprobar que los datos están bien gestionados ANTES de tener la app:
  [1] Escribir valores a mano      (p. ej. pendiente 3°, temperatura media 250 K, lluvia 0)
  [2] Parecidos a un punto de la Tierra   (lat, lon) → ¿salen sitios del mismo tipo?
  [3] Parecidos a un sitio de la Luna o Marte   (cuando existan sus fichas, tras el pendrive)
  [4] Estadísticas de una variable
  [5] Qué datos hay (resumen)

Fórmula: la del motor (src/analogs/similarity.py) con las tolerancias de configs/variables.yaml.
Lee: data/processed/fichas_tierra_h3r5.parquet (scripts/build_earth_features.py)
     data/processed/fichas_objetivos_*.parquet   (Luna / Marte, si existen)
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analogs.paths import CONFIGS, PROCESSED, VALIDATION  # noqa: E402
from analogs.similarity import analog_index, variable_scores  # noqa: E402

MALLAS = {  # nombre → (fichero, cómo se llama cada fila)
    "005deg": ("fichas_tierra_005deg.parquet", "píxeles de 0,05° (~5,6 km)"),
    "h3r5": ("fichas_tierra_h3r5.parquet", "hexágonos H3 res 5 (~17 km)"),
}
MALLA = "005deg"
if "--malla" in sys.argv:          # python scripts/buscar.py --malla h3r5
    MALLA = sys.argv[sys.argv.index("--malla") + 1]
EARTH_FILE = PROCESSED / MALLAS[MALLA][0]
UNIT_NAME = MALLAS[MALLA][1]
ENVS = {"1": "hielo polar", "2": "desierto (suelo desnudo)", "3": "árido abierto (matorral/estepa)"}


# ------------------------------------------------------------------ entrada por teclado
def ask(prompt: str, default: str = "") -> str:
    try:
        r = input(prompt).replace("﻿", "").strip()   # PowerShell añade un BOM al canalizar texto
    except EOFError:
        print()
        raise SystemExit(0)
    return r or default


def ask_float(prompt: str, unit: str = "") -> float | None:
    while True:
        r = ask(prompt).replace(",", ".").lower()
        if r == "":
            return None
        try:
            if unit == "K" and r.endswith("c"):          # se admite °C: "-20c"
                return float(r[:-1].replace("°", "")) + 273.15
            return float(r)
        except ValueError:
            print("   (escribe un número, o Enter para no usar esta variable)")


# ------------------------------------------------------------------ datos
def load() -> tuple[pd.DataFrame, dict, dict, pd.DataFrame]:
    if not EARTH_FILE.exists():
        raise SystemExit(f"No existe {EARTH_FILE}.\nEjecuta antes (una línea cada uno):\n"
                         f"   .venv\\Scripts\\python.exe scripts\\build_earth_mask.py\n"
                         f"   .venv\\Scripts\\python.exe scripts\\build_earth_features.py")
    earth = pd.read_parquet(EARTH_FILE)
    variables = yaml.safe_load((CONFIGS / "variables.yaml").read_text(encoding="utf-8"))["variables"]
    pruebas = yaml.safe_load((CONFIGS / "pruebas.yaml").read_text(encoding="utf-8"))["pruebas"]
    targets = [pd.read_parquet(f) for f in sorted(PROCESSED.glob("fichas_objetivos_*.parquet"))]
    targets = pd.concat(targets, ignore_index=True) if targets else pd.DataFrame()
    return earth, variables, pruebas, targets


def usable_vars(earth: pd.DataFrame, variables: dict) -> list[str]:
    """Variables de variables.yaml que existen en la Tierra con algún dato."""
    return [v for v in variables if v in earth.columns and earth[v].notna().any()]


def summary(earth: pd.DataFrame, variables: dict, targets: pd.DataFrame) -> None:
    m = earth[earth.in_mask]
    print(f"\n=== DATOS CARGADOS ===\nTierra: {len(earth):,} {UNIT_NAME} con tierra · "
          f"{len(m):,} dentro de la máscara (desiertos, hielo, zonas áridas)")
    for k, name in ENVS.items():
        print(f"   {name:34s} {int((m.env == int(k)).sum()):>8,}")
    print(f"\n{'variable':18s} {'unidad':7s} {'con dato':>9s}   {'mín':>8s} {'p5':>8s} {'mediana':>8s} {'p95':>8s} {'máx':>8s}")
    for v in usable_vars(earth, variables):
        s = m[v].dropna()
        unit = variables[v].get("unit", "")
        print(f"{v:18s} {unit:7s} {100 * len(s) / max(len(m), 1):8.0f}%   "
              + " ".join(f"{x:8.1f}" for x in (s.min(), s.quantile(.05), s.median(), s.quantile(.95), s.max())))
    missing = [v for v in variables if v not in usable_vars(earth, variables)]
    print(f"\nSin dato todavía en la Tierra: {', '.join(missing)}")
    if len(targets):
        print(f"Sitios objetivo: {len(targets)} ({', '.join(f'{b}: {n}' for b, n in targets.body.value_counts().items())})")
    else:
        print("Sitios objetivo (Luna/Marte): ninguno procesado aún → faltan los datos del pendrive")


# ------------------------------------------------------------------ búsqueda
def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def spread(df: pd.DataFrame, n: int, min_km: float) -> pd.DataFrame:
    """Los n mejores, pero separados al menos min_km (si no, salen 10 hexágonos vecinos del mismo sitio)."""
    kept = []
    for idx, r in df.iterrows():
        if all(haversine_km(r.lat, r.lon, df.at[k, "lat"], df.at[k, "lon"]) >= min_km for k in kept):
            kept.append(idx)
            if len(kept) == n:
                break
    return df.loc[kept]


def ask_filters(earth: pd.DataFrame) -> pd.DataFrame:
    print("\n--- Filtros (Enter = valor por defecto) ---")
    cells = earth
    if ask("¿Solo dentro de la máscara (desiertos/hielo/árido)? [S/n]: ", "s").lower().startswith("s"):
        cells = cells[cells.in_mask]
    env = ask("Tipo de zona: 1 hielo polar · 2 desierto · 3 árido abierto · Enter = todas: ")
    if env in ENVS:
        cells = cells[cells.env == int(env)]
    lat_min = ask_float("Latitud mínima (Enter = sin límite): ")
    lat_max = ask_float("Latitud máxima (Enter = sin límite): ")
    if lat_min is not None:
        cells = cells[cells.lat >= lat_min]
    if lat_max is not None:
        cells = cells[cells.lat <= lat_max]
    print(f"→ {len(cells):,} celdas candidatas")
    return cells


def ask_weights(vars_in_target: list[str], pruebas: dict) -> dict:
    names = ", ".join(pruebas)
    r = ask(f"\nPesos: Enter = todas las variables pesan igual · o escribe una prueba ({names}): ").lower()
    if r in pruebas:
        w = {k: v for k, v in pruebas[r]["weights"].items() if k in vars_in_target}
        if not w:
            print(f"   La prueba '{r}' usa variables que aún no tenemos → pesos iguales")
        else:
            print(f"   Prueba '{pruebas[r]['label']}': {w}\n   Validez: {pruebas[r]['test_validity']}")
            return w
    return {v: 1.0 for v in vars_in_target}


def run_search(target: dict, cells: pd.DataFrame, variables: dict, weights: dict, title: str,
               exclude_near: tuple[float, float] | None = None) -> None:
    scores = variable_scores(target, cells, {k: variables[k] for k in weights})
    idx = analog_index(scores, weights)
    res = cells.assign(indice=idx).join(scores.add_prefix("nota_"))
    res = res.dropna(subset=["indice"]).sort_values("indice", ascending=False)
    if exclude_near:
        d = haversine_km(exclude_near[0], exclude_near[1], res.lat.to_numpy(), res.lon.to_numpy())
        res = res[d >= 150]

    n = int(ask_float("¿Cuántos resultados? (Enter = 10): ") or 10)
    sep = ask_float("Separación mínima entre resultados en km (Enter = 100): ")
    top = spread(res.head(5000), n, 100 if sep is None else sep)

    print(f"\n=== {title} ===")
    print("Objetivo: " + " · ".join(f"{k} = {target[k]:.1f} {variables[k].get('unit', '')}" for k in weights))
    print(f"Celdas evaluadas: {len(res):,} · índice ≥ 90: {(res.indice >= 90).sum():,} · "
          f"≥ 75: {(res.indice >= 75).sum():,} · ≥ 50: {(res.indice >= 50).sum():,}\n")
    for rank, (_, r) in enumerate(top.iterrows(), 1):
        print(f"{rank:2d}. índice {r.indice:5.1f}   lat {r.lat:7.2f}  lon {r.lon:8.2f}   {r.env_name}")
        print("      " + " · ".join(f"{k} {r[k]:.1f} (nota {r['nota_' + k]:.2f})" for k in weights if pd.notna(r[k])))
        print(f"      https://www.google.com/maps/@{r.lat:.4f},{r.lon:.4f},9z")
    VALIDATION.mkdir(parents=True, exist_ok=True)
    out = VALIDATION / f"busqueda_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
    top.round(3).to_csv(out, index=False)
    print(f"\nGuardado: {out}")


def mode_manual(earth, variables, pruebas):
    vs = usable_vars(earth, variables)
    m = earth[earth.in_mask]
    print("\n--- Escribe el valor de cada variable (Enter = no usarla). Temperaturas en K o en °C con 'c' (p. ej. -20c) ---")
    target = {}
    for v in vs:
        s = m[v].dropna()
        spec = variables[v]
        val = ask_float(f"{spec['label']} ({spec.get('unit', '')}) [Tierra: {s.quantile(.05):.0f}–{s.quantile(.95):.0f}, "
                        f"mediana {s.median():.0f}; tolerancia {spec['tolerance']}]: ", spec.get("unit", ""))
        if val is not None:
            target[v] = val
    if not target:
        print("No has escrito ningún valor.")
        return
    cells = ask_filters(earth)
    run_search(target, cells, variables, ask_weights(list(target), pruebas), "SITIOS MÁS PARECIDOS A TUS VALORES")


def mode_earth_point(earth, variables, pruebas):
    lat = ask_float("Latitud del punto (p. ej. -24.1 para Atacama): ")
    lon = ask_float("Longitud del punto (p. ej. -70.0): ")
    if lat is None or lon is None:
        return
    d = haversine_km(lat, lon, earth.lat.to_numpy(), earth.lon.to_numpy())
    ref = earth.iloc[int(np.argmin(d))]
    vs = [v for v in usable_vars(earth, variables) if pd.notna(ref[v])]
    print(f"\nCelda más cercana ({d.min():.0f} km): {ref.env_name}, dentro de la máscara: {ref.in_mask}")
    for v in vs:
        print(f"   {variables[v]['label']:32s} {ref[v]:9.1f} {variables[v].get('unit', '')}")
    target = {v: float(ref[v]) for v in vs}
    cells = ask_filters(earth)
    run_search(target, cells, variables, ask_weights(vs, pruebas),
               f"SITIOS PARECIDOS A ({lat:.2f}, {lon:.2f}) — se excluyen los de < 150 km", exclude_near=(lat, lon))


def mode_target(earth, variables, pruebas, targets):
    if targets.empty:
        print("\nTodavía no hay fichas de la Luna ni de Marte en data/processed/.\n"
              "Cuando copies los datos del pendrive: python scripts/importar_datos.py <zip o carpeta>\n"
              "y después: python scripts/build_mars_features.py")
        return
    for k, r in targets.reset_index(drop=True).iterrows():
        print(f"  [{k}] {r['body']:5s} {r['name']}")
    k = ask_float("Número del sitio: ")
    if k is None or not 0 <= int(k) < len(targets):
        return
    t = targets.reset_index(drop=True).iloc[int(k)]
    vs = [v for v in usable_vars(earth, variables) if v in t.index and pd.notna(t[v])]
    if "precip_mm_year" in usable_vars(earth, variables):
        t = t.copy()
        t["precip_mm_year"] = 0.0      # en la Luna y Marte no llueve (variables.yaml)
        vs.append("precip_mm_year")
    if not vs:
        print("Ese sitio no comparte ninguna variable con la Tierra todavía.")
        return
    target = {v: float(t[v]) for v in vs}
    cells = ask_filters(earth)
    run_search(target, cells, variables, ask_weights(vs, pruebas), f"ANÁLOGOS EN LA TIERRA DE {t['name']} ({t['body']})")


def mode_stats(earth, variables):
    vs = usable_vars(earth, variables)
    for k, v in enumerate(vs):
        print(f"  [{k}] {v}")
    k = ask_float("Número de la variable: ")
    if k is None or not 0 <= int(k) < len(vs):
        return
    v = vs[int(k)]
    m = earth[earth.in_mask]
    s = m[v].dropna()
    print(f"\n{variables[v]['label']} ({variables[v].get('unit', '')}) — {len(s):,} celdas con dato")
    counts, edges = np.histogram(s, bins=12)
    for c, a, b in zip(counts, edges[:-1], edges[1:]):
        print(f"  {a:9.1f} – {b:9.1f} │{'█' * int(50 * c / counts.max()):50s}│ {c:,}")
    print("\nMediana por tipo de zona:")
    print(m.groupby("env_name")[v].describe(percentiles=[.5])[["count", "min", "50%", "max"]].round(1).to_string())


def main() -> None:
    earth, variables, pruebas, targets = load()
    summary(earth, variables, targets)
    menu = {"1": "Escribir valores a mano", "2": "Parecidos a un punto de la Tierra",
            "3": "Parecidos a un sitio de la Luna o Marte", "4": "Estadísticas de una variable",
            "5": "Resumen de los datos", "0": "Salir"}
    while True:
        print("\n" + " · ".join(f"[{k}] {v}" for k, v in menu.items()))
        op = ask("Opción: ")
        if op == "1":
            mode_manual(earth, variables, pruebas)
        elif op == "2":
            mode_earth_point(earth, variables, pruebas)
        elif op == "3":
            mode_target(earth, variables, pruebas, targets)
        elif op == "4":
            mode_stats(earth, variables)
        elif op == "5":
            summary(earth, variables, targets)
        elif op in ("0", "q", "salir"):
            break


if __name__ == "__main__":
    main()
