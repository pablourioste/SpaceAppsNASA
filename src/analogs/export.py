"""PASO 4: escribir el ÍNDICE que lee la app (app/data/).

La app no descarga datos de NASA: solo lee estos ficheros, que pesan pocos MB.
El formato está explicado en app/README.md. Lo usan tanto el flujo real
(scripts/run_pipeline.py) como los datos falsos (scripts/make_mock_data.py).

    app/data/config.json              variables, pruebas y el bloque "no análogo" de cada cuerpo
    app/data/objetivos.json           un objeto por sitio objetivo (Luna/Marte) con su ficha
    app/data/tierra.json              la ficha de cada hexágono de la Tierra, por columnas
    app/data/analogos_conocidos.json  análogos ya estudiados (para marcarlos y validar)
"""
import json

import numpy as np
import pandas as pd

from .paths import APP_DATA


def _clean(value, ndigits=3):
    """NaN → null y floats redondeados, para un JSON válido y ligero."""
    if isinstance(value, (float, np.floating)):
        return None if np.isnan(value) else round(float(value), ndigits)
    if isinstance(value, np.integer):
        return int(value)
    return value


def _write(name: str, payload) -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    with open(APP_DATA / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))


def write_index(targets: pd.DataFrame, earth: pd.DataFrame, variables_cfg: dict, pruebas: dict,
                known_analogs: pd.DataFrame | None = None, mock: bool = False) -> None:
    """Escribe los cuatro ficheros de app/data/.

    targets: una fila por objetivo; columnas id, name, body, lat, lon, type + variables
    earth:   una fila por hexágono; columnas cell_id, lat, lon + variables (+ operabilidad)
    """
    aviso = {"_aviso": "DATOS FALSOS generados por scripts/make_mock_data.py"} if mock else {}
    var_names = [v for v in variables_cfg["variables"] if v in earth.columns or v in targets.columns]

    _write("config.json", {**aviso,
                           "variables": variables_cfg["variables"],
                           "operability": variables_cfg.get("operability", {}),
                           "bodies": variables_cfg["bodies"],
                           "pruebas": pruebas})

    meta = ["id", "name", "body", "lat", "lon", "type"]
    objetivos = [{**{k: _clean(r[k]) for k in meta if k in r},
                  "features": {v: _clean(r[v]) for v in var_names if v in r}}
                 for r in targets.to_dict("records")]
    _write("objetivos.json", {**aviso, "objetivos": objetivos})

    _write("tierra.json", {**aviso,
                           "n_cells": len(earth),
                           "columns": {c: [_clean(x) for x in earth[c].tolist()] for c in earth.columns}})

    if known_analogs is not None:
        _write("analogos_conocidos.json",
               {"analogos": [{k: _clean(v) for k, v in r.items()} for r in known_analogs.to_dict("records")]})
