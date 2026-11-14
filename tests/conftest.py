"""Permite importar el paquete `analogs` (en src/) desde los tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
