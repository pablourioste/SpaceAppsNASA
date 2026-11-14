# Plan del sábado por la mañana (coordina Marc hasta que llegue Pablo, 14:30)

> **Objetivo:** llegar a las 14:30 con el enfoque decidido, cada persona con su tarea, las cuentas creadas, y **el motor y la app funcionando con datos falsos**.
> Lo que Pablo había previsto acordar (columnas de las fichas y formato para la app) ya está propuesto en el repo: [`configs/variables.yaml`](../configs/variables.yaml) y [`app/README.md`](../app/README.md). Solo hay que revisarlo.

## 1. Arranque (30 min)
- [ ] Todos leen [`01_como_funciona.md`](01_como_funciona.md) (15 min).
- [ ] Clonar el repo, crear el entorno y comprobar que funciona (ver el [README](../README.md#puesta-en-marcha)):
  `python -m pytest` en verde y `python scripts/make_mock_data.py` sin errores.
- [ ] Comprobar que todos pueden hacer push a una rama.
- [ ] Cada uno crea sus cuentas (gratis): **Earthdata Login**, **Copernicus Data Space**, **EODMS** (CSA) y **JAXA G-Portal**. Alguna puede tardar en activarse, así que mejor hacerlo ya.

## 2. Propuesta y decisión (60 min)
Marc presenta la propuesta (15 min) y se discute sobre ella, no sobre una hoja en blanco:
1. **Qué hacemos:** buscador de *matches* "¿qué quieres probar?" + modo inverso + validez de la prueba ([01 §1–§5](01_como_funciona.md)).
2. **Por qué así:** [03_enfoque.md](03_enfoque.md) §0 (en 6 líneas) y §5 (lo que NO es análogo).
3. **Decisiones con propuesta por defecto:** [03_enfoque.md §7](03_enfoque.md). Cambiar lo que haga falta.

Después (45 min): ideas nuevas del equipo y votación con la plantilla [`meetings/brainstorming.md`](meetings/brainstorming.md), con estos criterios: *¿encaja con el reto? ¿hay datos? ¿llega a tiempo? ¿luce en una demo?*
Apuntar lo decidido en [`decisions/README.md`](decisions/README.md).

## 3. Roles (15 min)
- [ ] Rellenar nombres en [`05_equipo_y_roles.md`](05_equipo_y_roles.md).
- [ ] Crear issues en GitHub con las primeras tareas (checklist de [01 §7](01_como_funciona.md)).

## 4. Trabajo en paralelo hasta las 14:30

| Rol | Primera tarea | Dónde |
|---|---|---|
| **Ciencia** | Elegir 3 regiones del polo sur lunar + 2–3 sitios de Marte y poner sus coordenadas **oficiales**. Revisar pesos y tolerancias. Etiquetar los análogos conocidos por dimensión | `data/catalogs/`, `configs/` |
| **Datos Luna/Marte** | Descargar Diviner PRP sur (`dlre_prp_south.tab`, ~605 MB) y sacar `temp_avg`, `temp_max` e `ice_depth` de las 3 regiones | `data/raw/moon/`, `notebooks/` |
| **Datos Tierra** | Primera capa global: temperatura de superficie MODIS (`MOD11C3`) con `earthaccess`. Después, relieve | `data/raw/earth/`, `notebooks/` |
| **Motor** | Preparar la malla H3 de la Tierra y el paso de fichas → índice (paso 3 → 4) | `src/analogs/` |
| **App** | Elegir librería (globe.gl / CesiumJS / Streamlit) y montar el globo leyendo `app/data/` (datos falsos): filtros, colorear, clic → ficha | `app/` |
| **Coordinación** | Confirmar el **formato y la hora de la entrega** en spaceappschallenge.org. Primer guion de la presentación | `presentation/` |

## 5. Sync con Pablo (14:30)
Preparar en 5 minutos:
1. Qué hemos decidido (y por qué).
2. Qué datos tenemos y qué falta.
3. Quién hace qué.
4. Dudas abiertas / bloqueos.
