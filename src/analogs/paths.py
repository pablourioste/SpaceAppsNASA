"""Rutas del proyecto. Importar desde aquí en vez de escribir rutas a mano.

La carpeta de datos se puede mover fuera del repo (p. ej. fuera de OneDrive)
definiendo la variable de entorno ANALOGS_DATA_DIR.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("ANALOGS_DATA_DIR", ROOT / "data"))

RAW = DATA / "raw"
EXTERNAL = ROOT / "data" / "external"  # catálogos pequeños, siempre dentro del repo
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"

CONFIGS = ROOT / "configs"
OUTPUTS = ROOT / "outputs"
RESULTS = OUTPUTS / "results"
FIGURES = OUTPUTS / "figures"
