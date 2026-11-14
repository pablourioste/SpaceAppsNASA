"""PASO 1: descargar los datos de las APIs  →  data/raw/{earth,moon,mars}/

Pendiente (equipos de datos). Reglas:
- Descargar SOLO lo necesario: productos L3/L4 (ya convertidos en variable física)
  y, si se puede, solo la zona de interés.
- Cada dataset descargado se apunta en el inventario de data/README.md.
- Nada de contraseñas en el código: earthaccess las pide o las lee de ~/.netrc.

Ejemplo (Tierra, Earthdata; requiere cuenta de Earthdata Login):

    import earthaccess
    earthaccess.login()                                   # pide usuario y contraseña
    res = earthaccess.search_data(short_name="MOD11C3",   # temperatura de superficie mensual
                                  temporal=("2023-01", "2023-12"))
    earthaccess.download(res, RAW / "earth" / "modis_lst")

Ejemplo (Luna, PDS; sin cuenta): el producto de recursos polares de Diviner es un único
fichero de texto (~605 MB) en
    https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/dlre_prp_south.tab
"""
from .paths import RAW  # noqa: F401  (para usar en los ejemplos de arriba)


def download_all() -> None:
    raise NotImplementedError("Paso 1 pendiente: ver la explicación en src/analogs/download.py")
