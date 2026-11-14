"""PASO 2: leer, recortar y remuestrear  →  data/interim/

Pendiente (equipos de datos).

Entra: los ficheros tal cual de data/raw/ (GeoTIFF, NetCDF/HDF, tablas).
Sale:  los mismos datos recortados a las zonas de interés y llevados a una malla común.

Cuidados (docs/03_enfoque.md §2):
- Cada cuerpo con su propio sistema de coordenadas: la Luna y Marte NO se mezclan con la Tierra.
- Pendiente y rugosidad: misma resolución en los tres cuerpos antes de compararlas.
- Longitudes: unificar a −180..180 este (algunos productos planetarios usan 0..360).

Librerías: rasterio / rioxarray / xarray (rásters), pandas (tablas como Diviner PRP).
"""


def prepare_all() -> None:
    raise NotImplementedError("Paso 2 pendiente: ver la explicación en src/analogs/ingest.py")
