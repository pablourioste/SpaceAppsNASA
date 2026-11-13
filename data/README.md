# data/ — datos de entrada

```
data/
├── raw/          # Datos tal cual se descargan o nos dan. NUNCA se modifican.
│   ├── provided/ #   lo que nos entregue la organización
│   ├── earth/
│   ├── moon/
│   └── mars/
├── external/     # Catálogos pequeños hechos a mano o de terceros (CSV, GeoJSON). SÍ van a git.
├── interim/      # Pasos intermedios (recortes, reproyecciones). Se pueden borrar y regenerar.
└── processed/    # Tablas de características finales que usa el motor de similitud.
```

## Reglas
1. **Los rásters y ficheros grandes NO se suben a git** (`.gitignore` ya ignora `raw/`, `interim/` y `processed/`). Se comparten por el Drive del equipo: _[enlace aquí]_.
2. El repo está en OneDrive en algún ordenador: **no meter GBs de datos dentro de la carpeta sincronizada**; mejor una carpeta local fuera y apuntar a ella (ver `src/analogs/paths.py`, variable de entorno `ANALOGS_DATA_DIR`).
3. Todo dataset descargado se apunta en la tabla de abajo (para reproducibilidad y para la entrega: hay que citar los datos de NASA usados).
4. Si un script descarga datos, va en `scripts/` y se indica aquí.

## Catálogos incluidos (`external/`)
| Fichero | Contenido | Estado |
|---|---|---|
| `known_analogs.csv` | Análogos terrestres conocidos → set de validación | Coordenadas aproximadas, **verificar** |
| `target_sites.csv` | Sitios objetivo en Luna/Marte (lon este, −180..180, planetocéntrico) | Aproximadas; faltan coords de Artemis III |

## Inventario de datasets
| Dataset | Cuerpo | Variable(s) | Resolución | Formato | Fuente / URL | Ubicación | Quién |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
