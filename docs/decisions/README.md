# Registro de decisiones

Una fila por decisión importante (alcance, datos, stack, método…). Si una decisión cambia, se añade una nueva fila que la sustituye; no se borra la antigua.

| # | Fecha | Decisión | Por qué | Alternativas descartadas | Quién |
|---|---|---|---|---|---|
| 001 | 2026-11-13 | Estructura provisional del repositorio | Que el equipo pueda empezar ordenado | — | Pablo |
| 002 | 2026-11-14 | **PROPUESTA:** índice de fichas precalculado (`app/data/`) + mapas y fotos en vivo; la app calcula los matches en el navegador | Los datos raw no cambian: se calculan una vez. Llamar a la API en cada clic tardaría minutos, pide contraseñas y depende de que NASA esté arriba durante la demo | Llamar a las APIs en cada consulta | Marc (a confirmar el sábado) |
| 003 | 2026-11-14 | **PROPUESTA:** comparar en unidades físicas con tolerancia (nota lineal), no con percentiles por cuerpo | Los percentiles emparejan "lo típico de Marte" con "lo típico de la Tierra" (ver `docs/03_enfoque.md` §2.1) | Percentiles / z-score por cuerpo; IA entrenada (no hay ejemplos etiquetados) | Marc (a confirmar el sábado) |
| 004 | 2026-11-14 | **PROPUESTA:** la app se organiza por "¿qué quieres probar?" (`configs/pruebas.yaml`) + modo inverso + validez de la prueba | Es como prueba un ingeniero (por subsistemas) y responde al *"connect your analog to exploration"* | Perfiles de misión genéricos | Marc (a confirmar el sábado) |
| 005 | 2026-11-14 | Reorganización del repo: docs numerados en orden de lectura, `data/external` → `data/catalogs`, `outputs/results` → `app/data`, `mission_profiles.yaml` → `variables.yaml` + `pruebas.yaml` | Que se entienda dónde va cada cosa | — | Marc |
| 006 | 2026-11-14 | Two separate resolutions. **Imagery** (what you see when zooming): as fine as possible (CTX ~5 m on Mars, Sentinel-2 ~10 m on Earth). **Data** (what the similarity index is computed from): moderate but **the same on every body**, at the ~10 km landing-ellipse footprint (MOLA 3.7 km and TES 3 km are fine; GRS ~300 km only gives regional context) | Imagery makes the demo; the index is only fair if both sides are measured at the same scale (slope and roughness change with DEM resolution, `docs/03_enfoque.md` §2.2) | Computing the index at the finest resolution available on each body | adriasolaf |
