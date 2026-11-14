# Enfoque propuesto (PROPUESTA para el brainstorming)

> Marc, 13/11/2026 (noche). Explica el *porqué* del método; el *cómo* está en [01_como_funciona.md](01_como_funciona.md). Respecto al [brief inicial de Pablo](referencia/brief_inicial.md) cambia sobre todo el **método**; donde no coincidan, manda este documento.
> **[verificar]** = no comprobado todavía · **[hipótesis]** = apuesta que el motor tiene que confirmar o tumbar · **[supuesto]** = valor elegido por nosotros.

---

## 0. En 6 líneas

1. **Producto = herramienta + historia.** Un buscador global y explicable de análogos (el *método*) **y** 2–3 análogos nuevos caracterizados a fondo (lo que *sorprende*). Uno sin el otro no gana.
2. **Similitud física, no parecido visual.** Como en un túnel de viento: no se reproduce el avión entero, se reproducen los parámetros que controlan lo que quieres medir. Para cada cosa que se quiere probar: ¿qué la controla y qué parte reproduce la Tierra?
3. **Unidad de comparación = una "huella" del tamaño de una elipse de aterrizaje (~10 km)**, con todas las variables calculadas a la **misma resolución** en los tres cuerpos.
4. **Puntuación por dimensión**, con lo que la Tierra *no puede* reproducir (gravedad, presión, radiación) siempre visible en la ficha.
5. **Foco:** polo sur lunar (el título del reto es *Permanent Moon Base*) + 2–3 sitios de Marte.
6. **Lo "nuevo" se mide:** similitud alta × lejos de análogos ya conocidos × accesible. Validamos con análogos conocidos **por perfil** y **contra un modelo nulo**.

---

## 1. Lo que el texto oficial completo añade al brief

El brief inicial solo tenía el *Summary*. El texto completo ([`02_reto_oficial.md`](02_reto_oficial.md)) pide explícitamente cosas que hoy no están en el plan:

| El enunciado dice | Implicación para nosotros |
|---|---|
| *"The goal is not simply to rediscover well-known analog sites"*; Antarctica, Atacama, Iceland, Hawaii *"already widely studied"* | Los análogos conocidos solo **validan**. Nunca son el resultado estrella. |
| *"Explain which characteristics… provide a strong analogy, where the analogy breaks down"* | Cada ficha: qué coincide, **cuánto** (con valores y unidades) y qué no. |
| *"Think about processes as well as places"* | Al menos una capa de **proceso** (polvo, erosión eólica, hielo) → stretch. |
| *"Consider scale"* (un cráter, un valle… no un continente) | Cribado global grueso → **refinamiento fino** en los candidatos (§2.5). |
| *"Explore the whole Earth, including below its surface"* | Capa de cuevas / tubos de lava. |
| *"Connect your analog to exploration"* | Cada ficha: **qué probarías aquí** (instrumento, operación, riesgo que reduces). |
| *"Remember Earth's limits"* (gravedad, vacío, atmósfera fina, radiación) | Bloque fijo "no análogo" en cada ficha (§5). |
| *"…as well as data and images obtained locally"* | Opcional: un análogo de proximidad con fotos o datos propios. |
| *"Surprise us"* | §4. |

---

## 2. Problemas que veo en la propuesta actual (y cómo los arreglaría)

### 2.1 ⚠️ Normalizar por percentiles dentro de cada cuerpo: error para variables físicas

El brief inicial proponía *"normalizar cada variable dentro de su cuerpo (percentiles o z-score)"*. Eso compara **posiciones relativas**, no condiciones. Ejemplo: la temperatura media de Jezero (≈ −60 °C, orden de magnitud [verificar con la Mars Climate Database]) es un valor *típico* de Marte → percentil ~50 → se emparejaría con el percentil 50 de la Tierra, es decir, con zonas templadas. Absurdo.

**Regla propuesta:**

- Variables con escala física común (pendiente en °, rugosidad a la misma línea base, albedo, abundancia de rocas en %, temperatura en K, tamaño de grano) → comparar **en unidades físicas** con una tolerancia:

$$
s_k = \max\!\left(0,\; 1 - \frac{\left|x_k^{\text{obj}} - x_k^{\text{T}}\right|}{\sigma_k}\right),
\qquad
S = 100\,\frac{\sum_{k} w_k\, s_k}{\sum_{k} w_k}
$$

  donde $x_k^{\text{obj}}$ es el valor de la variable $k$ en el sitio objetivo (Luna/Marte), $x_k^{\text{T}}$ el de la celda terrestre, $\sigma_k$ la tolerancia física de esa variable, es decir, la diferencia a partir de la cual la nota es 0 (p. ej. $\sigma_{\text{pendiente}} = 5^\circ$ [supuesto, lo fija Ciencia]), $w_k$ el peso de la prueba elegida ([`configs/pruebas.yaml`](../configs/pruebas.yaml)), $s_k \in [0,1]$ la nota de cada variable (lo que se pinta en el radar) y $S \in [0,100]$ el índice de analogía. Las sumas recorren solo las variables disponibles en ambos cuerpos.
  Está implementado en [`src/analogs/similarity.py`](../src/analogs/similarity.py), y el ejemplo de juguete de [01_como_funciona.md](01_como_funciona.md) es un test en [`tests/test_similarity.py`](../tests/test_similarity.py). Una alternativa más suave es la gaussiana $s_k = e^{-\frac12 (\Delta_k/\sigma_k)^2}$; se eligió la lineal porque es más fácil de explicar y llega a 0.
- **Variables categóricas** (litología): matriz de similitud entre clases, $s_k = M[c^{\text{obj}}, c^{\text{T}}]$, con p. ej. basalto–basalto = 1 [Ciencia rellena la matriz].
- **Percentiles** solo para índices sin escala física común (p. ej. índices espectrales de instrumentos distintos).
- Si la Tierra **no llega al rango**, $s_k \approx 0$ y la ficha lo marca como *no análogo*. Ejemplo: las regiones en sombra permanente (PSR) lunares están a unas decenas de K según Diviner; el mínimo terrestre medido por satélite es ≈ 175 K en la meseta antártica [verificar]. Eso es información útil, no un fallo del método.

### 2.2 ⚠️ Pendiente y rugosidad dependen de la resolución del DEM

MOLA ≈ 463 m/px, MOLA-HRSC ≈ 200 m/px, LOLA polar 5–80 m/px, Copernicus 30 m/px. En el mismo terreno, la pendiente calculada a 30 m sale mayor que a 500 m. Comparar pendientes de DEMs con distinta **línea base** es como comparar dos soluciones CFD en mallas distintas sin estudio de convergencia.

**Arreglo:** fijar una línea base común $L$ y remuestrear el DEM más fino antes de derivar pendiente y rugosidad:
- $L \approx 500$ m para la búsqueda global (lo que permite MOLA);
- $L \approx 100$ m solo en los casos de estudio donde haya DEM fino (HRSC/CTX en Marte, LOLA polar en la Luna).

Método de referencia: rugosidad de MOLA a varias líneas base, Kreslavsky & Head (2000) [verificar].

### 2.3 ⚠️ La inercia térmica no se puede comparar directamente entre la Tierra y Marte

El perfil `rover_mobility` usa `thermal_inertia`, $I = \sqrt{k \rho c}$ (en $\mathrm{J\,m^{-2}\,K^{-1}\,s^{-1/2}}$, con $k$ la conductividad, $\rho$ la densidad y $c$ el calor específico del suelo). Pero en un suelo granular $k$ depende de la presión del gas en los poros: ≈ 6 mbar en Marte frente a 1 bar en la Tierra. **El mismo $I$ no implica el mismo suelo** [verificar: Presley & Christensen, 1997]. En la Luna (vacío) el régimen es otro, y en la Tierra la "inercia térmica aparente" de satélite está contaminada por la humedad del suelo.

**Arreglo:** comparar la propiedad que le importa al rover, el **tamaño de grano / abundancia de rocas** (Marte: derivados de THEMIS/TES; Luna: *rock abundance* de Diviner; Tierra: fracción gruesa de SoilGrids) [verificar productos].

### 2.4 ⚠️ La iluminación del polo sur lunar no es la de los polos terrestres (salvo en una ventana concreta)

Oblicuidad: Luna 1,54°, Tierra 23,44°. Las regiones candidatas lunares están a menos de 6° del polo, así que allí el Sol nunca sube más de ~7,5° y da la vuelta al horizonte una vez por mes sinódico (29,5 días). En un polo terrestre hay 6 meses de día y el Sol sube hasta 23,4°.

Elevación máxima diaria del Sol a latitud $\varphi$ con declinación solar $\delta$ (sin refracción, ~0,5°):

$$
h_{\max} = 90^\circ - |\varphi - \delta|
$$

Cerca de un **equinoccio** ($\delta \approx 0$), a $|\varphi| \approx 83$–$88^\circ$ la Tierra reproduce durante unos días el **rango de elevación solar** de los sitios lunares. Pero:
- las sombras barren **~30× más rápido**: 15 °/h en la Tierra frente a 360°/708 h ≈ 0,5 °/h en la Luna;
- la atmósfera rellena las sombras con luz difusa. En la Luna las sombras son negras, salvo la luz que refleja el terreno.

Tierra emergida a esas latitudes: costa norte de Groenlandia (hasta ~83,6° N) y las montañas Transantárticas (hasta ~87° S) [verificar].
→ **Capa calculable con pura geometría**, sin descargar nada, y con un resultado contraintuitivo: para iluminación, Haughton (75,4° N, $h_{\max} \approx 15^\circ$ en el equinoccio) es *peor* análogo que el norte de Groenlandia.

### 2.5 Tamaño de la rejilla: las cuentas no salen

El brief habla de *"50k celdas a 5–10 km"*. La superficie emergida es ≈ 1,49·10⁸ km², así que a 10 km salen ~1,5·10⁶ celdas y a 5 km ~6·10⁶. 50k celdas corresponden a una rejilla de ~0,5° (~55 km). Además, una rejilla lat-lon regular degenera en los polos, y medio proyecto está en los polos.

**Arreglo en dos etapas (de grueso a fino):**
1. **Cribado global** en una malla de igual área: hexágonos H3 de resolución 4 (≈ 1770 km² por celda → ~8·10⁴ celdas de tierra) [supuesto: subir a res. 5, ~6·10⁵ celdas, si da tiempo].
2. **Refinamiento** a 30–90 m en ventanas de ~10 km alrededor de los top-N.

### 2.6 Validación: "si sale Atacama, funciona" es casi circular

Si el peso de la aridez es alto, **cualquier** desierto hiperárido sale arriba por construcción. Arreglo:
- Etiquetar cada análogo conocido con **qué dimensión** reproduce (terreno, química, frío, iluminación, operaciones) y validar **por perfil**. Hay que añadir una columna `dimension` a [`known_analogs.csv`](../data/catalogs/known_analogs.csv).
- Comparar con un **modelo nulo**: celdas aleatorias de la misma máscara (desiertos, polares…). Métrica, el factor de enriquecimiento

$$
E = \frac{\text{hit rate}@N\ \text{del motor}}{\text{hit rate}@N\ \text{de celdas aleatorias}}
$$

  $E \gg 1$: el motor discrimina. $E \approx 1$: solo estamos midiendo "es un desierto".
- Dos validaciones **específicas** muy potentes [verificar coordenadas antes de añadirlas al CSV]:
  - **Lago Salda (Turquía)**: NASA lo usó como análogo de los carbonatos de Jezero. Si el perfil "Jezero" lo encuentra sin decírselo, es una prueba fuerte.
  - **Cráter Mistastin (Labrador, Canadá)**: impacto sobre anortosita, usado como análogo de las tierras altas lunares.

### 2.7 Sitios objetivo lunares

- Las 9 regiones de [`target_sites.csv`](../data/catalogs/target_sites.csv) son de la actualización de NASA de **octubre de 2024**. En 2026 el programa ha cambiado: hay noticias de que Artemis III pasa a ser una demostración en órbita baja y el aterrizaje se traslada a Artemis IV, y NASA ha anunciado una *Moon Base* en el polo sur [verificar en nasa.gov]. → En el catálogo ya se ha cambiado el tipo `artemis iii candidate` por `south pole candidate region (NASA 2024)`.
- Faltan las coordenadas: sacarlas de los polígonos oficiales, **no rellenarlas a ojo**.

### 2.8 La app recibe fichas (valores, unidades y fuentes), no notas

Una ficha que dice "pendiente: 0,83" no convence. Una que dice "Marte 12° · Tierra 14° (MOLA-HRSC / Copernicus)" sí. Por eso el índice de `app/data/` guarda **los valores de cada variable** con su unidad y su fuente, y la app calcula las notas al momento. Así puede:
- enseñar los dos valores, con unidades y fuentes, en la ficha;
- recalcular con cualquier prueba o con pesos que el usuario mueva a mano;
- enseñar el bloque "no análogo" (gravedad, presión, duración del día) desde `config.json`.

El formato exacto está en [`app/README.md`](../app/README.md). La novedad (distancia al análogo conocido más cercano) se calcula en la app a partir de `analogos_conocidos.json`.

---

## 3. Cómo funcionaría

```
 OBJETIVO (Luna / Marte)                 TIERRA (global)
 ventana ~10 km alrededor del sitio      malla H3 res. 4 (~8·10⁴ celdas)
        │   mismas variables, misma L          │
        ▼                                      ▼
   vector x_obj ───── similitud por dimensión s_k ─────► S global + radar
                                                            │
             × novedad (lejos de análogos conocidos)        │
             × operabilidad (accesible, no protegido)       ▼
                                    top-N → refinamiento 30–90 m → fichas
```

**Salida visual clave:** gráfico **similitud frente a accesibilidad** con el frente de Pareto. Es lo que usaría de verdad un planificador de misión.

### Variables del MVP (las que existen en ambos cuerpos)

| Dimensión | Variable (unidad) | Luna | Marte | Tierra |
|---|---|---|---|---|
| Terreno | pendiente a $L$ (°) | LOLA (polar 20–80 m) | MOLA / MOLA-HRSC | Copernicus GLO-30 / Geomorpho90m |
| Terreno | rugosidad a $L$ (°, RMS de pendiente) | LOLA | MOLA | ídem |
| Geología | litología gruesa (clase) | Mapa geológico unificado (USGS) | Mapa global (USGS, Tanaka 2014) | GLiM |
| Superficie | abundancia de rocas / grano | Diviner | THEMIS / TES | SoilGrids (fracción gruesa) |
| Iluminación | rango de elevación solar (°) | geometría (+ mapas de iluminación LOLA) | geometría | geometría |
| Frío / hielo | $T_{\min}$ (K), hielo somero | Diviner, PSR | MCD, SWIM | MODIS LST, permafrost ESA CCI |
| Subsuelo | cuevas / tubos (presencia) | Lunar Pit Atlas (LROC) | MGC³ (USGS) | proxy: campos volcánicos basálticos (GVP + GLiM) |
| Operabilidad (*solo Tierra*) | tiempo a ciudad (h), zona protegida | — | — | Weiss et al. 2018, WDPA |

[verificar disponibilidad, resolución y formato de cada producto en el inventario de mañana. Si la pestaña Resources da otros, mandan esos.]

---

## 4. Apuestas para la historia ("Surprise us") [hipótesis]

**A. Luna: "la base irá a tierras altas, pero entrenamos en mares".**
El polo sur lunar es terreno de tierras altas (feldespático / anortosítico, en el borde de la cuenca Aitken) [verificar con el mapa geológico unificado]. Muchos análogos lunares clásicos son basálticos (Hawái, Lanzarote, Craters of the Moon, SP Crater), así que reproducen los **mares**, no las tierras altas donde irá la base. Habría que buscar litología anortosítica + latitud de iluminación rasante (§2.4) + permafrost + relieve de macizo.
Resultado probable: **ningún sitio lo cumple todo**, y eso lleva a la idea B.

**B. "Cartera de análogos" (*set cover*).**
En vez de buscar "el mejor sitio", buscar **el conjunto mínimo de 2–3 sitios** que entre todos cubren todas las dimensiones de un sitio objetivo. Por ejemplo, para Mons Mouton: geología en X, iluminación en Y, frío/hielo en Z. Con un algoritmo voraz se implementa en una tarde, y responde al reto de una forma nueva (*"an analog does not have to match everything"*).

**C. Marte: proceso, no solo lugar.** Ciencia elige uno de estos:
- yardangs (erosión eólica) de Medusae Fossae ↔ desierto de Lut (Irán), menos usado que Atacama [verificar];
- hielo somero de Arcadia Planitia (SWIM) ↔ permafrost rico en hielo.

---

## 5. Lo que NO es análogo (bloque fijo en cada ficha)

| | Luna | Marte | Tierra |
|---|---|---|---|
| Gravedad (m/s²) | 1,62 | 3,71 | 9,81 |
| Presión superficial (Pa) | ~0 (exosfera) | ≈ 610 (CO₂, varía con la estación) | 101 325 |
| Día solar | 29,5 d | 24,66 h (1 sol) | 24 h |
| Radiación en superficie | sin atmósfera ni magnetosfera | atmósfera fina, sin magnetosfera global | protegida por ambas |

Conviene decirlo en voz alta en el pitch porque da credibilidad. La tracción y el hundimiento del rover escalan con $g$, y la morfología de los cráteres también: la transición de cráter simple a complejo está en ~2–4 km en la Tierra, ~7 km en Marte y ~15–20 km en la Luna [verificar]. Así que un cráter "del mismo tamaño" **no** es un cráter análogo.

---

## 6. Alcance para 48 h (propuesta)

- **MVP (sábado noche):** 3 sitios lunares + 3 de Marte; Tierra en H3 res. 4; 4–5 variables; mapa + top-10 + ficha con valores; capa de iluminación; validación con modelo nulo.
- **Objetivo (domingo mediodía):** perfiles con pesos ajustables; novedad y operabilidad; refinamiento fino de 2–3 candidatos; fichas escritas (qué coincide / qué no / qué probarías).
- **Stretch:** cartera de análogos (§4B), capa de proceso (§4C), cuevas, modo inverso (Tierra → Luna/Marte).
- **Regla de oro:** el sábado por la noche tiene que existir un flujo **de punta a punta**, aunque sea con datos de juguete. Después se mejora cada pieza por separado.

[verificar la hora exacta de cierre de la entrega]

---

## 7. Decisiones del brainstorming, con propuesta por defecto

Para no partir de una hoja en blanco: se discute esta propuesta y se cambia lo que haga falta.

| Decisión | Propuesta | Por qué |
|---|---|---|
| Cuerpo(s) | Polo sur lunar + Marte, pocos sitios | El título del reto es *Moon Base*. La iluminación lunar sale gratis. Los objetivos son pocas ventanas, no mapas globales. |
| Sitios | Luna: 3 de las 9 regiones (las elige Ciencia por variedad de terreno). Marte: Jezero + Arcadia + Oxia | Mezcla de base humana y ciencia. Jezero tiene la "verdad sobre el terreno" de Perseverance. |
| Variables | Tabla de §3 | Existen en los dos cuerpos. |
| Método | Unidades físicas + tolerancia (§2.1), validación con modelo nulo (§2.6) | Defendible ante el jurado. |
| Malla de la Tierra | H3 res. 4 → refinamiento | §2.5 |
| UI | La que domine quien haga la app; sin servidor propio | Riesgo el día de la demo. |
| Datos de la Tierra | Google Earth Engine si alguien tiene cuenta; si no, productos globales ya agregados | Descargar el Copernicus DEM global no cabe en 48 h. |
| Presentación (≤ 7 diapositivas [verificar]) | Problema → principio (similitud física) → método → demo → validación → 2–3 análogos nuevos (qué sí / qué no) → límites e impacto | Una diapositiva por bloque. |

---

## 8. Para esta noche o a primera hora

- [ ] Revisar la pestaña **Resources** del reto y apuntar los datasets en [`data/README.md`](../data/README.md). Esta noche no ha sido posible abrir la web.
- [ ] Confirmar en spaceappschallenge.org el formato y la hora de la entrega.
- [ ] ¿Alguien tiene cuenta de **Google Earth Engine**? Si no, crearla (pide un proyecto de Google Cloud y puede tardar).
- [ ] Probar `pip install -r requirements.txt` en un portátil con Windows (rasterio y geopandas son los que suelen dar guerra).

## Referencias (todas [verificar] antes de citarlas en la entrega)

- Kreslavsky, M. A. & Head, J. W. (2000). Kilometer-scale roughness of Mars: results from MOLA data analysis. *JGR Planets*.
- Presley, M. A. & Christensen, P. R. (1997). Thermal conductivity measurements of particulate materials. *JGR Planets*.
- Weiss, D. J. et al. (2018). A global map of travel time to cities. *Nature*.
- Amatulli, G. et al. (2020). Geomorpho90m. *Scientific Data*.
- NASA (oct. 2024). Actualización de las regiones candidatas de aterrizaje en el polo sur lunar.
