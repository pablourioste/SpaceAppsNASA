"""PASO 3: construir las FICHAS  →  data/processed/

Pendiente (equipos de datos + motor).

Sale:
    data/processed/fichas_tierra.parquet     una fila por hexágono de la Tierra
    data/processed/fichas_objetivos.parquet  una fila por sitio objetivo de la Luna o Marte

Columnas: cell_id (o id), lat, lon y UNA COLUMNA POR VARIABLE de configs/variables.yaml,
con el mismo nombre y unidad. Lo que no exista en un cuerpo se deja vacío (NaN).
La Tierra lleva además las columnas de operabilidad (travel_time_h, protected_area).

Malla de la Tierra: hexágonos H3 de resolución 4 (≈ 1770 km² cada uno, ~8·10⁴ en tierra firme).
Objetivos: ventana de ~10 km alrededor de cada sitio de data/catalogs/target_sites.csv.
"""


def build_all() -> None:
    raise NotImplementedError("Paso 3 pendiente: ver la explicación en src/analogs/features.py")
