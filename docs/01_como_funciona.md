# Guía rápida: cómo funciona esto y todo lo que hay que hacer

> Para quien no ha tocado nunca la observación de la Tierra (o sea, todos nosotros). Marc, 14/11/2026.
> Complementa al [enfoque](03_enfoque.md): allí está el *porqué* del método; aquí, el *cómo* y la lista completa de tareas.
> **[verificar]** = no comprobado todavía.

---

## 1. La idea en una frase

**No comparamos fotos: comparamos la "ficha técnica" de cada sitio** (pendiente, temperatura, hielo, tipo de roca, iluminación…) y buscamos en la Tierra las fichas más parecidas a la de un sitio de la Luna o de Marte, **según lo que quieras probar**.

---

## 2. Qué es un "dato de satélite"

- **Ráster:** una imagen en la que cada píxel guarda **un número físico** y sabe en qué latitud y longitud está.
  - Una foto en color son 3 rásters: cuánta luz roja, verde y azul refleja el suelo.
  - Un **DEM** es un ráster de alturas (m). Una **LST** es un ráster de temperatura de superficie (K). Una imagen de **radar** es un ráster de eco (dB).
- **Resolución:** lo que mide un píxel sobre el suelo (30 m, 1 km…).
- **Formatos:** GeoTIFF (el más fácil), NetCDF / HDF5 (científicos: varias variables y fechas en un fichero) y tablas (CSV/TAB, como el PRP de Diviner).
- **Niveles de procesado (convención de NASA):**

  | Nivel | Qué es | ¿Lo usamos? |
  |---|---|---|
  | L0 | Señal bruta del instrumento | ❌ |
  | L1 | Calibrado (radiancias) | ❌ |
  | L2 | Variable física (p. ej. temperatura) en la geometría de cada pasada | Solo si no hay L3 |
  | **L3** | **Variable física en malla regular**, a menudo media mensual y global | ✅ **Lo normal** |
  | **L4** | Modelos o productos derivados (p. ej. profundidad del hielo de Diviner PRP) | ✅ |

  **Regla:** trabajamos con L3/L4. En L0 y L1 es donde se ahoga la gente.
- **Vectores:** puntos y polígonos (sitios, cráteres, volcanes) en CSV o GeoJSON.
- **Proyección (CRS):** cómo se aplana la esfera para hacer un mapa.
  - Lat/lon sirve para casi todo; en los polos se usa la estereográfica polar (LOLA polar, por ejemplo).
  - La Luna y Marte tienen sus propios sistemas, con otro radio: **no se mezclan con los de la Tierra**, cada cuerpo se procesa por separado.

> **Analogía CFD:** cada dataset es un campo escalar sobre su propia malla. El trabajo consiste en interpolarlos todos a una **malla común** y comparar celda a celda. Como en CFD, el ~70 % del esfuerzo es el **preproceso** (encontrar, descargar, recortar y remuestrear), no el "solver".

---

## 3. El flujo completo, de cero a la demo

```
 ① ¿Qué quieres probar?  →  ② ¿Qué variables lo controlan?  →  ③ ¿En qué dataset está cada variable?
                                                                   (Luna, Marte y Tierra)
            ↓
 ④ Descargar SOLO lo necesario  →  ⑤ Leer, recortar, malla común  →  ⑥ Derivados (pendiente, rugosidad…)
            ↓
 ⑦ Tabla de fichas (1 fila = 1 celda o sitio)  →  ⑧ Similitud ponderada  →  ⑨ Validar  →  ⑩ JSON → globo web
            ↓
 ⑪ Elegir 2–3 sitios nuevos y escribir sus fichas  →  ⑫ Presentación, vídeo y entrega
```

| Paso | Quién | Herramienta | Resultado |
|---|---|---|---|
| ①–② | Ciencia + Coordinación | Esta guía (§5) | Tabla "qué probar → variables → pesos" en `configs/` |
| ③ | Datos | Portales de [Resources](02_reto_oficial.md#resources-pestaña-oficial) | Inventario en `data/README.md` |
| ④–⑥ | Datos Luna/Marte · Datos Tierra | `earthaccess`, PDS/ODE, `rasterio`, `xarray` | `data/processed/` |
| ⑦–⑧ | Motor | `pandas`, `numpy`, `h3` | `data/processed/fichas_*.parquet` |
| ⑨ | Ciencia + Motor | Análogos conocidos + modelo nulo ([enfoque §2.6](03_enfoque.md)) | Gráfico de validación |
| ⑩ | Motor → App | Índice en `app/data/` ([formato](../app/README.md)) → globo web | App desplegada |
| ⑪ | Ciencia | Imágenes de Worldview / Trek a la misma escala | 2–3 fichas |
| ⑫ | Coordinación | Slides y vídeo | Entrega |

**Por qué un índice y no llamar a la API en cada clic.** Google no visita toda la web cuando buscas: la tiene indexada. Nosotros igual. Los datos de NASA se descargan y procesan **una vez** (pasos ④–⑦, decenas de GB que no van en la app) y se convierten en un **índice de fichas** de pocos MB (`app/data/`). La app calcula los *matches* sobre ese índice al instante, con cualquier filtro. Lo único que pide en vivo a NASA son los **mapas y fotos** al hacer zoom. Si aparece un sitio nuevo o una variable nueva, se vuelve a ejecutar el script y la app no se toca.

---

## 4. "¿Y la IA?"

- **Entrenar una IA** es enseñarle muchos ejemplos *con la respuesta correcta*. Para "este píxel es buen sitio para probar ruedas de Marte: sí/no" esas respuestas no existen: hay unos 20–50 análogos conocidos. Con eso un modelo no aprende nada fiable, y además no sabría explicar por qué.
- **Lo que hacemos:** **búsqueda por similitud**, es decir, buscar los vecinos más cercanos en el espacio de variables.
  - Es un algoritmo clásico de *machine learning* no supervisado: no necesita entrenamiento y se explica variable a variable.
  - El reto lo pide así: *"similarity metrics, machine learning"* y *"think beyond visual similarity"*.
- **Dónde sí meter ML si sobra tiempo (stretch):**
  - *k-means* para agrupar la Tierra en "familias de terreno";
  - comparar imágenes con un modelo preentrenado (p. ej. **Prithvi**, de NASA e IBM). El riesgo es que está entrenado con imágenes de la Tierra, así que en la Luna y en Marte trabaja fuera de lo que conoce.
- **Las fotos sí sirven,** pero para las **fichas y la demo** (comparación lado a lado y a la misma escala), no para el cálculo.
- **El "%" es un índice de analogía (0–100), no una probabilidad:** no está calibrado contra nada. En el pitch hay que decirlo así.

---

## 5. "¿Qué quieres probar?" → variables → datos

Es el corazón de la app. **Borrador para que Ciencia lo corrija.** Ya está en [`configs/pruebas.yaml`](../configs/pruebas.yaml) (pesos) y [`configs/variables.yaml`](../configs/variables.yaml) (fuentes y tolerancias):

| Quiero probar… | Lo controla | Luna / Marte (fuente) | Tierra (fuente) | Qué NO reproduce la Tierra y cómo se compensa |
|---|---|---|---|---|
| **Ruedas / movilidad** | pendiente, rugosidad, rocas, tamaño de grano | LOLA · Diviner (rocas) / MOLA · THEMIS | DEM (NASADEM / Copernicus) · SoilGrids [verificar] | Carga por rueda ∝ m·g → vehículo de prueba aligerado (JPL lo hizo con *Scarecrow* para Curiosity) |
| **Navegación autónoma / cámaras** | Sol rasante, sombras, sin vegetación, albedo | geometría solar · LROC / CTX | geometría solar · NDVI y albedo MODIS | Las sombras se mueven ~30× más rápido; la luz difusa del cielo rellena las sombras |
| **Perforación / muestras** | tipo de roca, suelo helado y cementado | mapas geológicos USGS · Diviner PRP | GLiM · permafrost (ESA CCI) | Material sí; temperatura del suelo no |
| **Detección de hielo** (radar, neutrones) | hielo en el subsuelo y su profundidad, rugosidad vista por radar | Diviner PRP (`ice_depth`) · Mini-RF · LEND / SWIM | permafrost (ESA CCI) · Sentinel-1 / RCM | Parcial: el hielo lunar está en vacío |
| **Energía solar y térmica** | iluminación, temperaturas extremas, ciclos | geometría · Diviner PRP / MCD | geometría · MODIS LST | La Tierra no baja de ≈ −90 °C ni llega al mediodía lunar (≈ +120 °C) |
| **Polvo, juntas, mecanismos** (Marte) | polvo en suspensión, viento | TES / MCD | MODIS AOD · MERRA-2 (viento) | Aire de Marte ~60× menos denso → el polvo se levanta de otra forma |
| **Hábitat / operaciones humanas** | aislamiento, frío, oscuridad, logística | — | tiempo de viaje a ciudades · LST · latitud | Radiación y gravedad no |
| **Comunicaciones** | relieve que tapa la línea de visión | LOLA / MOLA | DEM | La geometría sí se reproduce |

---

## 6. Herramientas y librerías

- **QGIS** (gratis): ver cualquier ráster sobre un mapa. **Es lo primero que hay que instalar.** Antes de programar nada, se abre el dato y se mira.
- **Python:**

  | Librería | Para qué |
  |---|---|
  | `numpy`, `pandas` | Números y tablas |
  | `rasterio`, `rioxarray`, `xarray` | Leer, recortar y remuestrear rásters (GeoTIFF, NetCDF) |
  | `geopandas` | Puntos y polígonos |
  | `h3` | Malla hexagonal de igual área |
  | `earthaccess` | Buscar y descargar de Earthdata con tu cuenta, en 3 líneas |
  | `pystac-client` | Buscar en Copernicus Data Space |
  | `scikit-learn` | Vecinos más cercanos, *k-means* |
  | `matplotlib`, `plotly` | Gráficos |

  Todas están en [`requirements.txt`](../requirements.txt).
- **Web:**
  - **globe.gl**: globo 3D en pocas líneas; admite texturas de la Luna y de Marte y capas de hexágonos [verificar].
  - **CesiumJS**: más potente, pero cuesta más aprenderlo.
  - Alternativa todo en Python: **Streamlit + pydeck**.
- **GitHub** para el código y **Drive** para los datos pesados.

---

## 7. Checklist de TODO el challenge

**A. Definición (Coordinación + Ciencia)**
- [ ] Enfoque del producto ("¿qué quieres probar?" + modo inverso).
- [ ] Sitios objetivo: 3 de la Luna y 2–3 de Marte, con coordenadas oficiales.
- [ ] Tabla §5 cerrada: variables, pesos y tolerancias σ por cada cosa que se quiere probar.

**B. Datos (Datos Luna/Marte + Datos Tierra)**
- [ ] Cuentas: Earthdata Login, Copernicus Data Space, EODMS, JAXA G-Portal.
- [ ] Inventario en `data/README.md`: cada dataset con fuente, resolución, formato y quién lo lleva.
- [ ] Huella de los objetivos: Diviner PRP + LOLA (Luna); MOLA + THEMIS (Marte).
- [ ] Capas globales gruesas de la Tierra (~1 km) para el cribado.
- [ ] Capas finas (30–90 m) **solo** alrededor de los candidatos.

**C. Motor**
- [ ] Malla H3 y tabla de fichas de la Tierra.
- [ ] Similitud por variable y global ([enfoque §2.1](03_enfoque.md); ya funciona: `src/analogs/similarity.py`).
- [ ] Novedad (distancia a análogos conocidos) y operabilidad (accesibilidad).
- [ ] Exportar JSON.

**D. Validación (Ciencia + Motor)**
- [ ] Análogos conocidos etiquetados por dimensión.
- [ ] Comparación con el modelo nulo (celdas aleatorias).
- [ ] Pruebas específicas: lago Salda ↔ Jezero, Mistastin ↔ tierras altas lunares.

**E. App**
- [ ] Globo con **datos falsos** desde el primer minuto (`python scripts/make_mock_data.py`).
- [ ] Selectores "qué probar" y "destino"; ficha con radar y valores.
- [ ] Modo inverso: clic en la Tierra → Luna y Marte.
- [ ] Desplegada con un enlace público.

**F. Contenido (Ciencia)**
- [ ] 2–3 fichas de sitios **nuevos**: qué se parece, qué no, qué probarías allí y qué validez tiene la prueba.
- [ ] Bloque fijo de límites (gravedad, presión, radiación).

**G. Entrega (Coordinación)**
- [ ] Título y resumen.
- [ ] Vídeo y/o slides [verificar formato].
- [ ] Enlace al repo y a la app.
- [ ] **Lista de datos usados, citados.**
- [ ] Declaración de uso de IA [verificar].
- [ ] **Hora límite** [verificar].

**H. Coordinación**
- [ ] Stand-up de 10 min cada ~3 h.
- [ ] Decisiones apuntadas en `docs/decisions/`.
- [ ] Recortar alcance sin piedad.

---

## 8. Ruta en el tiempo

| Cuándo | Objetivo |
|---|---|
| **Esta noche (vie → sáb)** | Marc: enfoque claro, tabla §5 en borrador, QGIS y Python instalados. |
| **Sábado mañana** | Todos crean cuentas y hacen el "hola mundo" (§9). Después, en paralelo: Datos Luna/Marte saca la huella lunar, Datos Tierra busca 2–3 capas, Motor conecta fichas e índice, App monta el globo con datos falsos y Ciencia cierra pesos y análogos. |
| **Sábado 14:30** | Sync con Pablo. |
| **Sábado tarde** | **Flujo de punta a punta**, aunque sea con 2 variables reales. |
| **Sábado noche** | Más variables, validación y modo inverso. |
| **Domingo mañana** | Congelar funcionalidades. Refinar 2–3 candidatos y escribir las fichas. |
| **Domingo hasta el cierre** | Slides, vídeo y entrega. **No tocar código en las últimas horas.** |

---

## 9. "Hola mundo" (30 min, para perder el miedo)

1. Instalar QGIS y el entorno de Python (ver el [README](../README.md#puesta-en-marcha)); `python -m pytest` tiene que salir en verde.
2. Bajar **un** ráster pequeño, por ejemplo un recorte del DEM de la zona donde estéis.
3. Abrirlo en QGIS y comprobar que "se ve bien".
4. Leerlo con Python y sacar el valor en un punto:

```python
import rasterio

with rasterio.open("dem.tif") as src:
    print(src.crs, src.res, src.bounds)        # sistema de referencia, tamaño de píxel, extensión
    lon, lat = 2.17, 41.39                      # ojo: rasterio pide (x, y) = (lon, lat)
    print(next(src.sample([(lon, lat)])))       # valor del píxel en ese punto
```

Si eso funciona, ya se sabe lo esencial: **un dato de satélite es una matriz de números con coordenadas.**

---

## 10. Glosario mínimo

| Término | Qué es |
|---|---|
| Ráster / píxel | Imagen de números; el píxel es una celda |
| Banda | Una de las "capas" de un ráster (p. ej. el rojo, o un canal infrarrojo) |
| DEM | Modelo digital de elevaciones (alturas) |
| LST | *Land Surface Temperature*: temperatura de la superficie vista desde el satélite |
| NDVI | Índice de vegetación (verde = alto) |
| Albedo | Fracción de luz que se refleja |
| SAR | Radar de apertura sintética: ve de día y de noche, a través de las nubes |
| Retrodispersión | Cuánta señal de radar vuelve al satélite; depende de la rugosidad y de la humedad |
| CPR | *Circular Polarization Ratio*: índice de radar sensible a la rugosidad y al hielo |
| Gránulo | Un fichero o escena concreta dentro de una colección de Earthdata |
| STAC | Estándar para buscar imágenes por zona y fecha (lo usa Copernicus) |
| Tesela / WMTS | Trocitos de mapa que carga la web (mapas base de Worldview y Trek) |
| L0–L4 | Niveles de procesado (§2) |
