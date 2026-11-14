"""Genera DATOS FALSOS en app/data/ para construir la app sin esperar a los datos reales.

    python scripts/make_mock_data.py

Los números son aleatorios y NO significan nada; los ficheros llevan "_aviso": "DATOS FALSOS".
Cuando el flujo real esté listo, scripts/run_pipeline.py sobrescribe app/data/ con datos de
verdad en el MISMO formato, y la app no hay que tocarla.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analogs.config import load_pruebas, load_variables  # noqa: E402
from analogs.export import write_index  # noqa: E402
from analogs.paths import APP_DATA, CATALOGS  # noqa: E402
from analogs.similarity import rank  # noqa: E402

RNG = np.random.default_rng(42)
N_CELLS = 3000

# Zonas de la Tierra donde caen los hexágonos falsos: (lat_min, lat_max, lon_min, lon_max)
ZONES = {
    "Sahara": (18, 30, -10, 30),        "Arabia": (17, 28, 40, 55),
    "Atacama": (-27, -18, -70, -66),    "Australia": (-30, -20, 120, 140),
    "Tibet-Gobi": (30, 45, 80, 105),    "SW USA": (32, 40, -118, -108),
    "Islandia": (63.5, 66, -22, -14),   "Groenlandia N": (78, 83, -60, -20),
    "Ártico canadiense": (72, 80, -100, -80), "Antártida": (-85, -70, -180, 180),
    "Patagonia": (-50, -40, -72, -66),  "Namib-Kalahari": (-28, -18, 12, 25),
}
# Oblicuidad (°): para una elevación solar máxima con algo de sentido (sin relieve)
OBLIQUITY = {"earth": 23.44, "moon": 1.54, "mars": 25.19}
# Rangos de temperatura falsos por cuerpo (K): (media_min, media_max, max_min, max_max)
T_RANGES = {"earth": (200, 305, 250, 340), "moon": (40, 250, 50, 390), "mars": (150, 240, 180, 300)}


def fake_features(lat: np.ndarray, body: str, categories: list) -> dict:
    n = len(lat)
    tm0, tm1, tx0, tx1 = T_RANGES[body]
    return {
        "slope_deg": RNG.uniform(0, 25, n),
        "roughness_deg": RNG.uniform(0, 12, n),
        "rock_abundance_pct": RNG.uniform(0, 40, n),
        "lithology": RNG.choice(categories, n),
        "sun_elev_max_deg": np.clip(90 - np.abs(lat) + OBLIQUITY[body], 0, 90),
        "t_mean_K": RNG.uniform(tm0, tm1, n),
        "t_max_K": RNG.uniform(tx0, tx1, n),
        "ice_depth_m": RNG.uniform(0, 3, n),
        "dust_aod": np.full(n, np.nan) if body == "moon" else RNG.uniform(0, 1, n),
        "caves": (RNG.random(n) < 0.1).astype(int),
    }


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main() -> None:
    variables_cfg = load_variables()
    categories = variables_cfg["variables"]["lithology"]["categories"]

    # --- Tierra: hexágonos falsos repartidos por las zonas ---
    zone_names = RNG.choice(list(ZONES), N_CELLS)
    box = np.array([ZONES[z] for z in zone_names])
    lat = RNG.uniform(box[:, 0], box[:, 1])
    lon = RNG.uniform(box[:, 2], box[:, 3])
    earth = pd.DataFrame({"cell_id": [f"mock_{i:05d}" for i in range(N_CELLS)], "lat": lat, "lon": lon,
                          **fake_features(lat, "earth", categories),
                          "travel_time_h": RNG.uniform(0, 48, N_CELLS),
                          "protected_area": (RNG.random(N_CELLS) < 0.2).astype(int)})

    # --- Objetivos: los sitios reales del catálogo (con coordenadas), con fichas falsas ---
    sites = pd.read_csv(CATALOGS / "target_sites.csv").dropna(subset=["lat", "lon"]).reset_index(drop=True)
    parts = []
    for body, grp in sites.groupby("body"):
        feats = pd.DataFrame(fake_features(grp["lat"].to_numpy(), body, categories), index=grp.index)
        parts.append(grp.join(feats))
    targets = pd.concat(parts).sort_index()
    targets.insert(0, "id", targets["name"].map(slug))

    known = pd.read_csv(CATALOGS / "known_analogs.csv")
    write_index(targets, earth, variables_cfg, load_pruebas(), known, mock=True)

    print(f"DATOS FALSOS escritos en {APP_DATA}")
    for f in sorted(APP_DATA.glob("*.json")):
        print(f"  {f.name:28s} {f.stat().st_size / 1024:8.1f} KB")

    # --- Demostración del motor (con datos falsos) ---
    t = targets.iloc[0]
    prueba = "ruedas"
    top = rank(t.to_dict(), earth, variables_cfg["variables"], load_pruebas()[prueba]["weights"], top=5)
    print(f"\nEjemplo (FALSO): prueba '{prueba}' para '{t['name']}' → 5 mejores celdas")
    print(top[["cell_id", "lat", "lon", "index"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
