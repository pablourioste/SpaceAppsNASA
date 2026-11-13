# Equipo y roles (plantilla)

> Plantilla provisional para 6 personas. Los nombres se rellenan en el brainstorming.
> Cada rol tiene un **responsable principal**, pero nadie trabaja aislado: los pares indicados se sincronizan a menudo.

## Resumen

| # | Rol | Responsable | Apoyo | Carpeta principal |
|---|---|---|---|---|
| R1 | Coordinación, producto y pitch | _____ | R2 | `docs/`, `presentation/` |
| R2 | Ciencia planetaria y validación | _____ | R1, R5 | `docs/`, `data/external/`, `configs/` |
| R3 | Datos de Luna y Marte | _____ | R4 | `data/`, `scripts/`, `src/analogs/ingest.py` |
| R4 | Datos de la Tierra | _____ | R3 | `data/`, `scripts/`, `src/analogs/ingest.py` |
| R5 | Motor de similitud / ML | _____ | R2, R3, R4 | `src/analogs/`, `notebooks/`, `outputs/` |
| R6 | Interfaz (UI/UX + frontend) | _____ | R1, R5 | `app/` |

```
            R2 Ciencia ──── define criterios ────┐
                                                 ▼
 R3 Datos Luna/Marte ─┐                    R5 Motor de similitud ──► outputs/results (JSON) ──► R6 UI
 R4 Datos Tierra ─────┴─ features ─────────►                                                    │
                                                                                                ▼
                                        R1 Coordinación: integra, prioriza, demo, vídeo, entrega
```

---

## R1 — Coordinación, producto y pitch
**Misión:** que al final haya un producto que funcione y una historia que se entienda.
- Facilitar el brainstorming y fijar el **alcance del MVP** (y defenderlo de añadidos).
- Mantener el tablero de tareas (GitHub Issues/Projects o Trello) y las horas de sincronización.
- Escribir el resumen del proyecto y la página de entrega de Space Apps.
- **Guion del vídeo/presentación desde el día 1**; grabar demo final.
- Control de tiempos: cortar lo que no llegue.
- **Entregables:** `docs/` al día, `presentation/`, entrega oficial.

## R2 — Ciencia planetaria y validación
**Misión:** que lo que decimos sea científicamente defendible.
- Decidir **qué variables** importan para cada perfil de misión y con qué pesos (`configs/mission_profiles.yaml`).
- Elegir los **sitios objetivo** de Luna/Marte (`data/external/target_sites.csv`).
- Mantener la lista de **análogos conocidos** (`data/external/known_analogs.csv`) → set de validación.
- Revisar resultados: ¿tienen sentido los top-10? Escribir las fichas de los sitios nuevos.
- Redactar el apartado de **limitaciones** (qué no es análogo).
- **Entregables:** criterios, pesos, validación, textos de las fichas.

## R3 — Datos de Luna y Marte
**Misión:** tener las variables planetarias listas en una rejilla común.
- Inventariar los datos que nos den + buscar los que falten (LOLA, Diviner, MOLA, THEMIS, TES, SWIM…).
- Descargar a `data/raw/moon|mars/`, documentar la fuente en `data/README.md`.
- Reproyectar/remuestrear y calcular derivados (pendiente, rugosidad…) → `data/processed/`.
- Conseguir las **teselas de NASA Trek** para el mapa base de la UI (con R6).
- **Entregables:** tabla de características por sitio/celda de Luna y Marte.

## R4 — Datos de la Tierra
**Misión:** lo mismo que R3 pero para la Tierra.
- Definir la máscara de **zonas candidatas** (desiertos, polares, volcánicas, áridas) para no procesar todo el planeta.
- DEM (Copernicus), clima (ERA5/WorldClim), aridez, litología (GLiM), mineralogía (ASTER/EMIT), permafrost, accesibilidad.
- Valorar **Google Earth Engine** para no descargar terabytes.
- **Entregables:** tabla de características por celda terrestre (mismas columnas que R3).

> R3 y R4 deben acordar **el mismo esquema de columnas** al principio (ver `src/analogs/features.py`).

## R5 — Motor de similitud / ML
**Misión:** convertir las tablas en un ranking explicable.
- Normalización entre cuerpos, métrica de similitud, pesos por perfil.
- Puntuación por variable (para el gráfico radar) + puntuación global.
- Ejecutar la **validación** con los análogos conocidos (top-N hit rate).
- Exportar lo que consume la UI: `outputs/results/*.json` / GeoJSON.
- *Stretch:* embeddings de imágenes/DEM con un modelo preentrenado.
- **Entregables:** `src/analogs/similarity.py`, notebook de validación, ficheros para la UI.

## R6 — Interfaz (UI/UX + frontend)
**Misión:** que un jurado entienda y use la herramienta en 30 segundos.
- Mockup rápido (papel/Figma) en las primeras horas → validarlo con R1.
- Dos mapas (Luna/Marte ↔ Tierra), selector de perfil de misión, lista top-N, ficha con radar.
- Trabajar con **datos falsos** (mock JSON) desde el principio para no esperar al motor.
- Despliegue (GitHub Pages / Vercel / Streamlit Cloud).
- **Entregables:** `app/` funcionando y desplegada.

---

## Normas de trabajo

- **Git:** una rama por tarea (`feat/ui-map`, `data/mola-dem`…), Pull Request a `main`, commits pequeños.
- **Datos pesados fuera de git** (ver `data/README.md`). En git solo código, configs, CSV pequeños y resultados ligeros.
- **Contrato entre piezas:** el formato de `outputs/results/*.json` se acuerda pronto y se documenta en `outputs/README.md`. Si cambia, se avisa.
- **Decisiones:** una línea en `docs/decisions/README.md` cada vez que se decide algo importante.
- **Sincronizaciones:** stand-up de 10 min cada ~3 h: qué hice / qué haré / qué me bloquea.

## Disponibilidad

| Persona | Rol | Disponible | Contacto |
|---|---|---|---|
| Pablo | _____ | desde 14:30 | _____ |
| _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ |
| _____ | _____ | _____ | _____ |
