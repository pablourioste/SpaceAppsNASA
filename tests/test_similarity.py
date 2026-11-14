"""Pruebas del motor con el ejemplo de juguete de docs/01_como_funciona.md.

Objetivo en Marte: pendiente 8°, rocas 15 %, temperatura −50 °C (números inventados).
Tolerancias: 10°, 20 %, 60 °C.

            pendiente  rocas  temperatura   │  ruedas  térmico  todo
  A Sáhara      2°       2 %     +25 °C     │   37.5     0.0    25.0
  B Islandia    7°      20 %       0 °C     │   82.5    16.7    60.6
  C Antártida  10°      10 %     −20 °C     │   77.5    50.0    68.3
"""
import numpy as np
import pandas as pd
import pytest

from analogs.similarity import analog_index, rank, variable_scores

VARIABLES = {
    "slope": {"type": "numeric", "tolerance": 10},
    "rocks": {"type": "numeric", "tolerance": 20},
    "temp": {"type": "numeric", "tolerance": 60},
}
TARGET = {"slope": 8, "rocks": 15, "temp": -50}
CELLS = pd.DataFrame({"slope": [2, 7, 10], "rocks": [2, 20, 10], "temp": [25, 0, -20]},
                     index=["A_sahara", "B_islandia", "C_antartida"])


def test_notas_por_variable():
    s = variable_scores(TARGET, CELLS, VARIABLES)
    assert s.loc["A_sahara"].tolist() == pytest.approx([0.40, 0.35, 0.0])
    assert s.loc["B_islandia"].tolist() == pytest.approx([0.90, 0.75, 1 / 6])
    assert s.loc["C_antartida"].tolist() == pytest.approx([0.80, 0.75, 0.50])


@pytest.mark.parametrize("weights, expected", [
    ({"slope": 1, "rocks": 1}, [37.5, 82.5, 77.5]),             # ruedas → gana Islandia
    ({"temp": 1}, [0.0, 100 / 6, 50.0]),                        # térmico → gana la Antártida
    ({"slope": 1, "rocks": 1, "temp": 1}, [25.0, 60.556, 68.333]),  # todo → gana la Antártida
])
def test_indice_segun_lo_que_quieres_probar(weights, expected):
    idx = analog_index(variable_scores(TARGET, CELLS, VARIABLES), weights)
    assert idx.tolist() == pytest.approx(expected, abs=1e-3)


def test_ranking_ruedas():
    top = rank(TARGET, CELLS, VARIABLES, {"slope": 1, "rocks": 1}, top=3)
    assert top.index.tolist() == ["B_islandia", "C_antartida", "A_sahara"]


def test_dato_que_falta_no_cuenta():
    """Si a una celda le falta una variable, los pesos se reparten entre las que tiene."""
    cells = CELLS.copy()
    cells.loc["B_islandia", "rocks"] = np.nan
    idx = analog_index(variable_scores(TARGET, cells, VARIABLES), {"slope": 1, "rocks": 1})
    assert idx["B_islandia"] == pytest.approx(90.0)   # solo cuenta la pendiente (0.90)


def test_variable_que_no_existe_en_el_objetivo():
    """Ej.: polvo en la Luna. Esa variable se ignora, no da error."""
    s = variable_scores({"slope": 8}, CELLS, VARIABLES)
    assert list(s.columns) == ["slope"]


def test_categorica():
    variables = {"rock": {"type": "categorical", "matrix": {"basalt": {"anorthosite": 0.3}}}}
    cells = pd.DataFrame({"rock": ["basalt", "anorthosite", "sedimentary", None]})
    s = variable_scores({"rock": "basalt"}, cells, variables)["rock"]
    assert s.iloc[:3].tolist() == [1.0, 0.3, 0.0]
    assert np.isnan(s.iloc[3])
