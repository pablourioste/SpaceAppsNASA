"""Cálculo de la tabla de características por celda/sitio (R3, R4, R5).

Esquema provisional de columnas (acordar entre R3, R4 y R5):

    cell_id, body, lat, lon,
    elevation, slope, roughness, rock_abundance,
    albedo, thermal_inertia,
    mean_temperature, temperature_range, aridity, ground_ice, sun_elevation,
    composition, caves, isolation

Una columna que no exista para un cuerpo se deja vacía (NaN) y no entra en la comparación.
Salida: data/processed/features_<body>.parquet
"""
