# outputs/ — resultados (salida)

- `results/` — ficheros que consume la app (contrato R5 ↔ R6). Ligeros → sí van a git.
- `figures/` — gráficos para docs y presentación.
- `maps/` — mapas exportados (PNG/HTML).

## Formato de `results/` (provisional, acordar)
```json
{
  "target": {"name": "Jezero", "body": "mars", "lat": 18.44, "lon": 77.45},
  "profile": "rover_mobility",
  "matches": [
    {"name": "…", "lat": 0.0, "lon": 0.0, "score": 0.87, "known_analog": false,
     "per_variable": {"slope": 0.9, "roughness": 0.8, "albedo": 0.6}}
  ]
}
```
