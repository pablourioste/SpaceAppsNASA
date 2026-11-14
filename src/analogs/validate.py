"""VALIDACIÓN: ¿el motor encuentra los análogos que ya se conocen?  →  outputs/validation/

Pendiente (ciencia + motor). Idea (docs/03_enfoque.md §2.6):
1. Para cada prueba, ver si los análogos conocidos de data/catalogs/known_analogs.csv
   que reproducen esa dimensión salen entre los N primeros.
2. Comparar con celdas elegidas al azar de la misma zona (modelo nulo):
       E = (aciertos del motor en el top-N) / (aciertos de celdas aleatorias en el top-N)
   E mucho mayor que 1 → el motor discrimina. E ≈ 1 → solo está detectando "es un desierto".
"""


def run_validation() -> None:
    raise NotImplementedError("Validación pendiente: ver la explicación en src/analogs/validate.py")
