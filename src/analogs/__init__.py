"""Buscador de análogos terrestres de la Luna y Marte.

Un fichero por paso del flujo:

    download.py    paso 1  APIs → data/raw/
    ingest.py      paso 2  data/raw/ → data/interim/        (recortar, malla común)
    features.py    paso 3  data/interim/ → data/processed/  (fichas)
    export.py      paso 4  data/processed/ → app/data/      (índice para la app)
    similarity.py  motor   la fórmula de parecido (la app usa la misma)
    validate.py    validación con análogos conocidos → outputs/validation/

    paths.py       rutas
    config.py      lee configs/variables.yaml y configs/pruebas.yaml
"""
