# notebooks/ — pruebas y exploración

Para mirar datos, probar ideas y hacer gráficos rápidos. **No es el sitio del código definitivo.**

- Nombre: `NN_iniciales_tema.ipynb` (p. ej. `01_mc_diviner_prp.ipynb`).
- Lo que funcione y se vaya a reutilizar se pasa a `src/analogs/`.
- Antes de hacer commit: **borrar las salidas pesadas** (imágenes grandes, tablas enormes).
- Para importar el código del proyecto desde un notebook:

```python
import sys; sys.path.insert(0, "../src")
from analogs.paths import RAW, PROCESSED
```
