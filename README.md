# 🌍🌕🔴 Earth Analogs for Moon & Mars — NASA Space Apps 2026

> **Estado: PROPUESTA** (14/11/2026). Se confirma en el brainstorming del sábado.

**Reto:** *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.* Enunciado completo en [`docs/02_reto_oficial.md`](docs/02_reto_oficial.md).

**Qué hacemos:** un **buscador de *matches***. Eliges **qué quieres probar** (ruedas, perforación, navegación…) y **para dónde** (un sitio de la Luna o de Marte). El globo vuela hasta los sitios de la Tierra que más se parecen y los enseña con un **índice de 0 a 100** y una ficha que explica qué se parece, qué no y qué validez tiene la prueba.

## Cómo funciona

```
 1. DATOS (Python, una vez)            2. MOTOR                       3. APP (navegador)
    satélites → fichas de números  →   fórmula de parecido       →   globo 3D: filtros, vuelo, ficha
    data/  ·  src/analogs/             src/analogs/similarity.py      app/  (lee app/data/)
```

Los datos de NASA se descargan y procesan **una vez** y se convierten en un **índice de fichas** de pocos MB (`app/data/`). La app calcula los *matches* al momento sobre ese índice, con cualquier filtro. Lo único que pide en vivo a NASA son los mapas y las fotos. Si aparece un sitio o una variable nueva, se vuelve a ejecutar el script y **la app no se toca**.

## 👉 Empieza aquí (en este orden)

1. [`docs/01_como_funciona.md`](docs/01_como_funciona.md): para quien no ha tocado nunca datos de satélite.
2. [`docs/02_reto_oficial.md`](docs/02_reto_oficial.md): el enunciado completo y los recursos oficiales.
3. [`docs/03_enfoque.md`](docs/03_enfoque.md): el método y por qué.
4. [`docs/04_plan_sabado.md`](docs/04_plan_sabado.md): qué hacemos el sábado por la mañana.
5. [`docs/05_equipo_y_roles.md`](docs/05_equipo_y_roles.md): quién hace qué.
6. [`docs/06_datos_luna.md`](docs/06_datos_luna.md): qué datos de la Luna recogemos, de qué fichero y cómo.

## Dónde va cada cosa

```
SpaceAppsNASA/
├── README.md                ← estás aquí
├── docs/                    LEER: documentación, numerada en orden de lectura
│   ├── decisions/           registro de decisiones
│   ├── meetings/            actas (plantilla de brainstorming)
│   └── referencia/          brief inicial (contexto, glosario, datasets)
├── configs/                 QUÉ SE COMPARA
│   ├── variables.yaml       la ficha: variables, unidades, tolerancias y fuentes
│   └── pruebas.yaml         "¿qué quieres probar?" = pesos de cada variable
├── data/                    DATOS (ver data/README.md)
│   ├── catalogs/            sitios objetivo (Luna/Marte) y análogos conocidos   [en git]
│   ├── raw/                 paso 1: tal cual se descarga (earth/, moon/, mars/)  [NO git]
│   ├── interim/             paso 2: recortado y en malla común                   [NO git]
│   └── processed/           paso 3: fichas, una fila por sitio o hexágono        [NO git]
├── src/analogs/             CÓDIGO: un fichero por paso (ver src/analogs/__init__.py)
├── scripts/                 LO QUE SE EJECUTA: run_pipeline.py, make_mock_data.py
├── app/                     LA APP · app/data/ = el índice que lee (paso 4)
├── outputs/                 PARA PERSONAS: figures/, maps/, validation/
├── notebooks/               pruebas y exploración
├── presentation/            slides, vídeo, imágenes
└── tests/                   pruebas automáticas (el ejemplo de juguete del motor)
```

## El flujo de los datos

```
  APIs de NASA/ESA/CSA/JAXA
        │  paso 1  src/analogs/download.py
        ▼
  data/raw/          tal cual
        │  paso 2  src/analogs/ingest.py
        ▼
  data/interim/      recortado, malla común
        │  paso 3  src/analogs/features.py
        ▼
  data/processed/    FICHAS  (fichas_tierra.parquet, fichas_objetivos.parquet)
        │  paso 4  src/analogs/export.py
        ▼
  app/data/          ÍNDICE  (config.json, objetivos.json, tierra.json, analogos_conocidos.json)
        │
        ▼
  app/               el navegador calcula los matches con la fórmula de src/analogs/similarity.py
```

Todo el flujo se lanza con `python scripts/run_pipeline.py`. Hoy se para en el paso 1, que está pendiente. Mientras tanto, `python scripts/make_mock_data.py` llena `app/data/` con **datos falsos** en el mismo formato, para que la app pueda avanzar.

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate             # Windows   (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest                   # el motor funciona → 8 passed
python scripts/make_mock_data.py   # datos FALSOS en app/data/ para empezar la app
```

**Datos pesados fuera de git y de OneDrive/Dropbox:** van en `C:\Users\<tú>\SpaceAppsData` (`raw/`, `interim/`, `processed/`) y el código la encuentra sola; para otra ruta, `setx ANALOGS_DATA_DIR <ruta>` y terminal nueva. Qué hay, cómo se procesa y cómo se comparte: [`docs/08_datos_LEEME.md`](docs/08_datos_LEEME.md) (se copia como `LEEME.md` dentro de la carpeta de datos con `scripts\inventario.py --leeme`). Índice de scripts: [`scripts/README.md`](scripts/README.md). Los catálogos de sitios siguen en `data/catalogs/` (en git).

## Cómo trabajamos

- Una rama por tarea → Pull Request a `main`.
- Datos pesados **fuera de git** (Drive compartido). En git: código, configs, catálogos e índice.
- Decisiones importantes en [`docs/decisions/`](docs/decisions/README.md).
- **[verificar]** = no comprobado · **[supuesto]** = valor elegido por nosotros, a revisar.

## Equipo

| Rol | Persona |
|---|---|
| Coordinación y presentación | |
| Ciencia y validación | |
| Datos de la Luna y Marte | |
| Datos de la Tierra | |
| Motor | |
| App | |
