"""Flujo completo con datos REALES: APIs → fichas → índice para la app.

    python scripts/run_pipeline.py

Los pasos 1–3 están pendientes (ver src/analogs/). Mientras tanto, este script se para en
el primero que falte y dice cuál es. Cuando estén todos, deja app/data/ con datos de verdad
en el mismo formato que scripts/make_mock_data.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from analogs import download, features, ingest, validate  # noqa: E402
from analogs.config import load_pruebas, load_variables  # noqa: E402
from analogs.export import write_index  # noqa: E402
from analogs.paths import CATALOGS, PROCESSED  # noqa: E402


def main() -> None:
    download.download_all()     # paso 1: APIs → data/raw/
    ingest.prepare_all()        # paso 2: data/raw/ → data/interim/
    features.build_all()        # paso 3: data/interim/ → data/processed/
    write_index(                # paso 4: data/processed/ → app/data/
        pd.read_parquet(PROCESSED / "fichas_objetivos.parquet"),
        pd.read_parquet(PROCESSED / "fichas_tierra.parquet"),
        load_variables(), load_pruebas(),
        pd.read_csv(CATALOGS / "known_analogs.csv"),
    )
    validate.run_validation()   # → outputs/validation/


if __name__ == "__main__":
    main()
