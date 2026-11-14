"""Lectura de configs/variables.yaml y configs/pruebas.yaml."""
import yaml

from .paths import CONFIGS


def load_variables() -> dict:
    """Devuelve el contenido completo de variables.yaml (variables, operability, bodies)."""
    with open(CONFIGS / "variables.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pruebas() -> dict:
    """Devuelve {id_prueba: {label, weights, test_validity}}."""
    with open(CONFIGS / "pruebas.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["pruebas"]
