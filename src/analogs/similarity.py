"""MOTOR: ¿cuánto se parece cada sitio de la Tierra a un sitio objetivo de la Luna o Marte?

Dos pasos (el ejemplo completo con números está en tests/test_similarity.py):

1. Nota por variable, de 0 a 1:
       numérica:    nota = 1 − |x_objetivo − x_tierra| / tolerancia      (mínimo 0)
       categórica:  nota = matriz[objetivo][tierra]   (sin matriz: igual = 1, distinto = 0)
   Si falta el dato en la Tierra o en el objetivo, esa nota queda vacía (NaN).

2. Índice de 0 a 100 = media ponderada de las notas disponibles, con los pesos de la
   prueba elegida (configs/pruebas.yaml). Las notas vacías no cuentan: los pesos se
   reparten entre las que sí existen.

El índice es un ÍNDICE DE ANALOGÍA, no una probabilidad (no está calibrado contra nada).
La app debe usar exactamente la misma fórmula (en JavaScript) sobre las fichas de app/data/.
"""
import numpy as np
import pandas as pd


def variable_scores(target: dict, cells: pd.DataFrame, variables: dict) -> pd.DataFrame:
    """Nota (0–1) de cada variable para cada celda de la Tierra.

    target:    ficha del objetivo, p. ej. {"slope_deg": 8, "rock_abundance_pct": 15, ...}
    cells:     una fila por celda de la Tierra, una columna por variable
    variables: el bloque "variables" de configs/variables.yaml
    """
    scores = {}
    for name, spec in variables.items():
        if name not in cells.columns:
            continue
        t = target.get(name)
        if t is None or (isinstance(t, float) and np.isnan(t)):
            continue  # el objetivo no tiene esta variable (p. ej. polvo en la Luna)

        col = cells[name]
        if spec.get("type", "numeric") == "numeric":
            s = (1.0 - (col - t).abs() / spec["tolerance"]).clip(lower=0.0)
        else:
            row = (spec.get("matrix") or {}).get(t, {})
            s = col.map(lambda c: row.get(c, 1.0 if c == t else 0.0)).astype(float)
            s = s.where(col.notna())
        scores[name] = s
    return pd.DataFrame(scores, index=cells.index)


def analog_index(scores: pd.DataFrame, weights: dict) -> pd.Series:
    """Índice de analogía (0–100): media ponderada de las notas disponibles."""
    w = pd.Series({k: v for k, v in weights.items() if k in scores.columns and v > 0}, dtype=float)
    if w.empty:
        return pd.Series(np.nan, index=scores.index)
    s = scores[w.index]
    num = (s.fillna(0.0) * w).sum(axis=1)
    den = (s.notna() * w).sum(axis=1)
    return 100.0 * num / den.replace(0.0, np.nan)


def rank(target: dict, cells: pd.DataFrame, variables: dict, weights: dict, top: int = 10) -> pd.DataFrame:
    """Las `top` celdas más parecidas, con su índice y la nota de cada variable."""
    scores = variable_scores(target, cells, variables)
    out = cells.join(scores.add_prefix("score_"))
    out["index"] = analog_index(scores, weights)
    return out.sort_values("index", ascending=False).head(top)
