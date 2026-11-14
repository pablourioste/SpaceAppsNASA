# scripts/ — lo que se ejecuta

| Script | Qué hace | Estado |
|---|---|---|
| `make_mock_data.py` | Llena `app/data/` con **datos falsos** (mismo formato que los reales) y enseña un ejemplo del motor | ✅ funciona |
| `run_pipeline.py` | Flujo completo con datos reales: APIs → fichas → `app/data/` → validación | ⏳ se para en el paso 1 (pendiente) |

Se ejecutan desde la raíz del repo: `python scripts/make_mock_data.py`.
La lógica va en `src/analogs/`; aquí solo se llama a esa lógica en orden.
Si un script descarga datos, se apunta en el inventario de [`data/README.md`](../data/README.md).
