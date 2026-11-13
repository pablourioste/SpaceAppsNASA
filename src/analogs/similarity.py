"""Motor de similitud (R5).

Idea provisional:
1. Normalizar cada variable dentro de su cuerpo (percentiles o z-score).
2. Para un sitio objetivo (Luna/Marte), calcular la similitud con cada celda terrestre
   usando solo las variables comunes, ponderadas según configs/mission_profiles.yaml.
3. Devolver puntuación global + puntuación por variable (para el gráfico radar).
4. Validar: ¿aparecen los análogos de data/external/known_analogs.csv en el top-N?
"""
