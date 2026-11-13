# 🌍🌕🔴 Earth Analogs for Moon & Mars — NASA Space Apps 2026

> **Estado: PROVISIONAL.** Estructura y nombre de trabajo; se cierran en el brainstorming.

**Reto:** *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.*
Usar datos abiertos de la Tierra, la Luna y Marte para encontrar y caracterizar **nuevos análogos terrestres** de futuras bases y zonas de aterrizaje, y presentarlos en un mapa/herramienta.

**Idea de partida:** una interfaz donde pinchas un sitio de la Luna o Marte, eliges qué quieres probar (rover, hielo, hábitat…) y obtienes los lugares de la Tierra más parecidos, con una ficha que explica por qué.

## 👉 Empieza aquí
1. [`docs/01_challenge_brief.md`](docs/01_challenge_brief.md) — el reto, datos, ideas y preguntas probables.
2. [`docs/02_equipo_y_roles.md`](docs/02_equipo_y_roles.md) — los 6 roles y normas de trabajo.
3. [`docs/03_plan_manana.md`](docs/03_plan_manana.md) — qué hacer en la primera mañana.

## Estructura

```
SpaceAppsNASA/
├── docs/                  # Documentación del equipo
│   ├── 01_challenge_brief.md
│   ├── 02_equipo_y_roles.md
│   ├── 03_plan_manana.md
│   ├── decisions/         # Registro de decisiones
│   └── meetings/          # Actas (plantilla de brainstorming)
├── data/                  # ENTRADA (input) — ver data/README.md
│   ├── raw/               #   datos originales: provided/, earth/, moon/, mars/  (no van a git)
│   ├── external/          #   catálogos pequeños: análogos conocidos, sitios objetivo (sí van a git)
│   ├── interim/           #   pasos intermedios (no van a git)
│   └── processed/         #   tablas de características finales (no van a git)
├── notebooks/             # Exploración (NN_iniciales_tema.ipynb)
├── src/analogs/           # Código Python del pipeline: ingest → features → similarity → export
├── scripts/               # Scripts sueltos: descargas, ejecución del pipeline
├── configs/               # Parámetros: perfiles de misión y pesos
├── app/                   # Interfaz de usuario (stack por decidir)
├── outputs/               # SALIDA (output)
│   ├── results/           #   JSON/GeoJSON que consume la app
│   ├── figures/           #   gráficos
│   └── maps/              #   mapas exportados
├── presentation/          # Slides, guion y vídeo de la entrega
└── tests/
```

**Flujo:** `data/raw` → `src/analogs` → `data/processed` → `outputs/results` → `app/`

## Puesta en marcha (Python)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   ·   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Cómo trabajamos
- Una rama por tarea → Pull Request a `main`.
- Datos pesados **fuera de git** (Drive compartido).
- Decisiones importantes en [`docs/decisions/`](docs/decisions/README.md).

## Equipo
| Rol | Persona |
|---|---|
| R1 Coordinación y pitch | |
| R2 Ciencia y validación | |
| R3 Datos Luna/Marte | |
| R4 Datos Tierra | |
| R5 Motor de similitud | |
| R6 Interfaz | |
