"""Rutas del proyecto. Importar desde aquí en vez de escribir rutas a mano.

Los datos pesados se pueden mover fuera del repo (p. ej. fuera de OneDrive)
definiendo la variable de entorno ANALOGS_DATA_DIR.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Entrada pequeña (en git) ---
CATALOGS = ROOT / "data" / "catalogs"   # sitios objetivo (Luna/Marte) y análogos conocidos
CONFIGS = ROOT / "configs"              # variables.yaml (qué se compara) y pruebas.yaml (pesos)

# --- Datos pesados (NO en git) ---
DATA = Path(os.environ.get("ANALOGS_DATA_DIR", ROOT / "data"))
RAW = DATA / "raw"              # paso 1: tal cual se descarga  (earth/, moon/, mars/)
INTERIM = DATA / "interim"      # paso 2: recortado y remuestreado
PROCESSED = DATA / "processed"  # paso 3: fichas (una fila por sitio o hexágono)

# --- Salida ---
APP_DATA = ROOT / "app" / "data"    # paso 4: el índice que lee la app
OUTPUTS = ROOT / "outputs"          # para personas: figuras, mapas, validación
FIGURES = OUTPUTS / "figures"
MAPS = OUTPUTS / "maps"
VALIDATION = OUTPUTS / "validation"
