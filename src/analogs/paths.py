"""Rutas del proyecto. Importar desde aquí en vez de escribir rutas a mano.

Los datos pesados viven FUERA del repo (no caben en git y OneDrive los bloquea).
La carpeta de datos (DATA) se busca en este orden:
  1. variable de entorno ANALOGS_DATA_DIR
  2. (Windows) la misma variable guardada con `setx`, aunque la terminal se abriera antes
  3. ~/SpaceAppsData   (C:\\Users\\<tú>\\SpaceAppsData): basta con copiar la carpeta ahí
  4. <repo>/data       (lo antiguo, por compatibilidad)
Dentro de DATA siempre: raw/<earth|moon|mars>/<carpeta>/, interim/, processed/, LEEME.md
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Entrada pequeña (en git) ---
CATALOGS = ROOT / "data" / "catalogs"   # sitios objetivo (Luna/Marte) y análogos conocidos
CONFIGS = ROOT / "configs"              # variables.yaml (qué se compara) y pruebas.yaml (pesos)

# --- Datos pesados (NO en git) ---
def _data_dir() -> Path:
    """ANALOGS_DATA_DIR del proceso; si no está (terminal abierta antes de definirla con setx),
    se lee la variable de usuario de Windows directamente del registro."""
    value = os.environ.get("ANALOGS_DATA_DIR")
    if not value and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value = winreg.QueryValueEx(key, "ANALOGS_DATA_DIR")[0]
        except OSError:
            value = None
    if value:
        return Path(value)
    home = Path.home() / "SpaceAppsData"
    return home if home.is_dir() else ROOT / "data"


DATA = _data_dir()
RAW = DATA / "raw"              # paso 1: tal cual se descarga  (earth/, moon/, mars/)
INTERIM = DATA / "interim"      # paso 2: recortado y remuestreado
PROCESSED = DATA / "processed"  # paso 3: fichas (una fila por sitio o hexágono)

# --- Salida ---
APP_DATA = ROOT / "app" / "data"    # paso 4: el índice que lee la app
OUTPUTS = ROOT / "outputs"          # para personas: figuras, mapas, validación
FIGURES = OUTPUTS / "figures"
MAPS = OUTPUTS / "maps"
VALIDATION = OUTPUTS / "validation"
