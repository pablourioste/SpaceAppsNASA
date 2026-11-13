# Challenge brief — Análogos terrestres de la Luna y Marte

> Documento **preliminar** (13/11/2026). Sirve para llegar al brainstorming con contexto común.
> Todo lo que hay aquí se puede cambiar. Lo marcado con ⚠️ hay que verificarlo en la web oficial de Space Apps.

---

## 1. El reto en una frase

**Usar datos abiertos de la Tierra, la Luna y Marte (NASA y otras agencias) para encontrar y caracterizar NUEVOS lugares en la Tierra que se parezcan a futuras bases o zonas de aterrizaje en la Luna o Marte, y presentarlo como un mapa, visualización o herramienta.**

- **Evento:** 2026 NASA Space Apps Challenge
- **Dificultad:** Beginner/Youth · Intermediate · Advanced (es abierto: se puede hacer simple o muy ambicioso)
- **Temas:** Earth Science · Planets & Moons · Software · Space Exploration

### Texto original

> Selecting future landing sites and lunar base locations depends on many factors, including topography, geology, environment, and available resources, to name a few. Places on Earth that have analogous characteristics to the Moon or Mars – the Atacama Desert, Haughton Crater, Death Valley – allow mission teams to test equipment and methods before they fly; however, such terrestrial analog sites are not entirely well characterized. Your challenge is to use open Earth, Moon, and Mars data from NASA and other space agencies to identify and characterize new terrestrial analogs for future bases or landing sites, drawing on deserts, polar regions, volcanic and arid terrains, caves, and other environments that share conditions with the lunar or Martian surface, then present your findings as a map, visualization, or other tool.

### Lo que piden realmente (desglosado)

| Verbo del enunciado | Qué significa para nosotros |
|---|---|
| **use open data** (Earth + Moon + Mars) | Tenemos que usar datos de los **tres** cuerpos, no solo de la Tierra. Citar las fuentes. |
| **identify** new analogs | Proponer sitios **nuevos**, no solo listar Atacama/Death Valley. |
| **characterize** | Para cada sitio: *por qué* se parece (qué variables coinciden y cuáles no). |
| for future **bases or landing sites** | El punto de partida es un sitio objetivo en Luna/Marte (p. ej. polo sur lunar de Artemis, Jezero…). |
| deserts, polar, volcanic, arid, **caves** | Tipos de terreno a considerar. Las cuevas/tubos de lava son un plus (bases protegidas de radiación). |
| present as **map, visualization or tool** | Entregable visual e interactivo → nuestra UI. |

---

## 2. Conceptos clave (mini-glosario)

| Término | Qué es |
|---|---|
| **Análogo terrestre** | Lugar de la Tierra que reproduce *algunas* condiciones de otro cuerpo (terreno, mineralogía, frío, aridez, luz…). Nunca todas. |
| **DEM** | Modelo digital de elevación (ráster de alturas). Base para pendiente, rugosidad, cráteres. |
| **Albedo** | Fracción de luz reflejada por la superficie. |
| **Inercia térmica** | Lo rápido que se calienta/enfría el suelo; indica si es polvo fino, arena o roca. |
| **Regolito** | Capa de polvo y fragmentos sueltos que cubre la Luna/Marte. |
| **PSR** | *Permanently Shadowed Regions*: cráteres del polo sur lunar que nunca ven el Sol (hielo de agua). |
| **ISRU** | *In-Situ Resource Utilization*: usar recursos locales (hielo, regolito) en vez de traerlos. |
| **EVA** | Actividad extravehicular (astronautas fuera del hábitat). |
| **Tubo de lava** | Cueva volcánica. Existen en Luna y Marte ("skylights"). Candidatas a bases. |
| **WMTS / tiles** | Servicio de teselas de mapa. NASA Trek ofrece mapas de Luna y Marte así. |

### Qué SÍ y qué NO puede ser análogo

| Puede ser análogo ✅ | No puede ser análogo ❌ (decirlo explícitamente = credibilidad) |
|---|---|
| Topografía: pendientes, rugosidad, cráteres | Gravedad (1/6 g Luna, 0,38 g Marte) |
| Geología/mineralogía: basaltos, sulfatos, óxidos de hierro, evaporitas | Vacío (Luna) / atmósfera de CO₂ a ~6 mbar (Marte) |
| Clima: frío extremo, hiperaridez, ciclos térmicos | Radiación cósmica y solar (solo parcialmente) |
| Iluminación: sol bajo y sombras largas (polos terrestres ≈ polo sur lunar) | Temperaturas extremas lunares (−170 °C / +120 °C) |
| Hielo en el subsuelo / permafrost | |
| Tubos de lava y cuevas | |
| Aislamiento logístico (operaciones de misión) | |

---

## 3. Análogos conocidos (punto de partida y **set de validación**)

Lista semilla en [`data/external/known_analogs.csv`](../data/external/known_analogs.csv) (coordenadas aproximadas, verificar).

| Sitio | País | Análogo de | Por qué |
|---|---|---|---|
| Desierto de Atacama | Chile | Marte | Hiperárido, suelos oxidantes con percloratos, UV alto |
| Cráter Haughton (Devon Island) | Canadá | Marte / Luna | Cráter de impacto en desierto polar (HMP) |
| Death Valley | EE. UU. | Marte | Playas, evaporitas, abanicos aluviales |
| Valles Secos de McMurdo | Antártida | Marte | Desierto frío hiperárido, permafrost |
| Río Tinto | España | Marte | Aguas ácidas ricas en hierro, jarosita (como Meridiani) |
| Lanzarote (Timanfaya, tubos de lava) | España | Luna / Marte | Basaltos, tubos de lava; ESA PANGAEA |
| Teide (Tenerife) | España | Marte | Pruebas de rovers (ExoMars) |
| Mauna Kea / Kīlauea | EE. UU. (Hawái) | Luna / Marte | Regolito basáltico; PISCES, HI-SEAS |
| Islandia (Askja, Holuhraun) | Islandia | Luna / Marte | Basaltos, volcanismo bajo hielo; entrenamiento Apolo |
| SP Crater / Black Point lava flow | EE. UU. | Luna | Campañas Desert RATS |
| Meteor Crater | EE. UU. | Luna | Geología de impacto, entrenamiento Apolo |
| Cráter de Ries | Alemania | Luna | Impactitas; entrenamiento Apolo 14 |
| MDRS (Hanksville, Utah) | EE. UU. | Marte | Simulación de hábitat |
| Svalbard (Bockfjord) | Noruega | Marte | Volcanes + hielo; expediciones AMASE |
| Craters of the Moon | EE. UU. | Luna | Campos de lava basáltica |
| Sudbury | Canadá | Luna | Estructura de impacto; entrenamiento Artemis |
| Pilbara | Australia | Marte | Astrobiología (estromatolitos antiguos) |
| Cráter Lonar | India | Luna / Marte | Impacto en basalto |
| Dallol | Etiopía | Marte | Ambiente hiperácido e hipersalino |

> 💡 **Idea de validación muy potente:** si nuestro algoritmo, sin decirle nada, pone Atacama o Haughton en el top-N para Marte, demuestra que funciona. Y entonces los sitios *nuevos* que salgan al lado son creíbles.

---

## 4. Sitios objetivo en la Luna y Marte (los que el usuario "picaría")

Lista semilla en [`data/external/target_sites.csv`](../data/external/target_sites.csv).

**Luna**
- **Regiones candidatas de Artemis III (polo sur):** Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, Mons Mouton, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2, Slater Plain ⚠️ (lista de la actualización de NASA de 2024; comprobar si hay cambios).
- Cráter Shackleton, PSRs del polo sur.
- Sitios Apolo 11–17, Chang'e 4 (cara oculta), Chandrayaan-3.
- Tubos de lava / skylights: Marius Hills, Mare Tranquillitatis pit.

**Marte**
- Sitios de aterrizaje históricos: Viking 1/2, Pathfinder, Spirit (Gusev), Opportunity (Meridiani), Phoenix, Curiosity (Gale), InSight (Elysium), Perseverance (Jezero), Zhurong (Utopia).
- Futuros/humanos: Oxia Planum (Rosalind Franklin), Arcadia Planitia y latitudes medias con hielo somero (proyecto **SWIM**), "Exploration Zones" del workshop de NASA de 2015.
- Cuevas: skylights de Arsia Mons.

---

## 5. Datos abiertos candidatos

> Mañana nos darán datos: **lo primero es mirar qué cubren** y encajarlos en esta tabla. No hace falta usarlo todo; con 3–5 variables bien elegidas por cuerpo basta para un MVP.

### Luna
| Dataset | Qué da | Dónde |
|---|---|---|
| LRO **LOLA** DEM (global ~118 m; polos 5–20 m) | Elevación → pendiente, rugosidad | PDS Geosciences, Moon Trek |
| LRO **LROC** WAC/NAC | Imágenes, mosaico global | LROC / Moon Trek |
| LRO **Diviner** | Temperatura, abundancia de rocas, propiedades del regolito | PDS |
| Mapas de **iluminación** y **PSR** del polo sur | % de horas de sol, sombra permanente | PDS / Moon Trek |
| LEND / Lunar Prospector, **M3** (Chandrayaan-1) | Hidrógeno / agua / OH, mineralogía | PDS |
| Mapa geológico unificado de la Luna (USGS, 1:5M) | Unidades geológicas | USGS Astrogeology |
| Kaguya/SELENE (JAXA) | DEM y imágenes | JAXA DARTS |

### Marte
| Dataset | Qué da | Dónde |
|---|---|---|
| **MOLA** DEM (~463 m) / MOLA-HRSC blend (~200 m) | Elevación, rugosidad | USGS Astrogeology, Mars Trek |
| **CTX** global mosaic (~5 m), **HiRISE** (~25 cm, local) | Imágenes | Murray Lab, HiRISE |
| **THEMIS** | Inercia térmica, IR día/noche | ASU / PDS |
| **TES** | Albedo, polvo, inercia térmica | PDS |
| **CRISM** (NASA), **OMEGA** (ESA) | Mineralogía (filosilicatos, sulfatos…) | PDS / PSA |
| **SWIM** (Subsurface Water Ice Mapping) | Probabilidad de hielo somero | NASA/JPL |
| **Mars Climate Database** (LMD/ESA) | Temperatura, presión, polvo | MCD |
| Mapa geológico global de Marte (USGS, Tanaka 2014) | Unidades geológicas | USGS Astrogeology |

### Tierra
| Dataset | Qué da | Dónde |
|---|---|---|
| **Copernicus DEM GLO-30** / SRTM / ASTER GDEM | Elevación 30 m | ESA/OpenTopography/Earthdata |
| **Landsat 8/9**, **Sentinel-2** | Imágenes multiespectrales | USGS/Copernicus/Earth Engine |
| **ASTER GED** | Emisividad → proxy de mineralogía (sílice, basalto) | NASA Earthdata |
| **EMIT** (ISS) | Mineralogía superficial de zonas áridas | NASA Earthdata |
| **MODIS** LST / albedo | Temperatura superficial, albedo | NASA Earthdata |
| **ERA5** / WorldClim | Clima (temperatura, precipitación) | Copernicus CDS / WorldClim |
| Índice de aridez global (CGIAR) | Aridez | CGIAR-CSI |
| **GLiM** | Litología global | PANGAEA |
| Earth Impact Database | Cráteres de impacto | PASSC |
| Smithsonian GVP | Volcanes | Smithsonian |
| Permafrost (NSIDC / ESA CCI) | Hielo en el suelo | NSIDC |
| VIIRS luces nocturnas, OSM carreteras | Aislamiento / accesibilidad | NASA / OSM |

### Plataformas útiles
- **NASA Moon Trek / Mars Trek** (trek.nasa.gov): visores + **servicios de teselas** que podemos meter directamente en nuestra UI.
- **NASA Earthdata / GIBS / Worldview**: datos y teselas de la Tierra.
- **Google Earth Engine**: procesar rásters terrestres sin descargarlos (cuenta gratuita para uso no comercial).
- **PDS** (NASA) y **PSA** (ESA): archivos planetarios.
- **Europlanet** (catálogo de sitios análogos) → etiquetas para validar.

---

## 6. ¿Qué podemos construir? (ideas para el brainstorming)

### Idea principal — "Analog Finder"
Interfaz con **dos mapas lado a lado**:
1. A la izquierda, Luna o Marte (teselas de NASA Trek). El usuario **pica un punto o un sitio predefinido** (p. ej. Mons Mouton, Jezero).
2. Elige un **perfil de misión** (qué quiere probar).
3. A la derecha, la Tierra con un **mapa de calor de similitud** y el **top-10 de sitios** compatibles.
4. Al pinchar un sitio terrestre: **ficha** con gráfico de radar (qué variables coinciden y cuáles no), fotos, accesibilidad, y si ya es un análogo conocido o es **NUEVO**.

### Cómo funciona por dentro (propuesta)
1. **Vector de características comparable** entre cuerpos, por celda de una rejilla (p. ej. 5–10 km en la Tierra):
   - Terreno: pendiente media, rugosidad, relieve local, densidad de cráteres.
   - Superficie: albedo, inercia térmica / tamaño de grano, abundancia de rocas.
   - Composición (categorías gruesas): basáltico, rico en hierro, sulfatos/evaporitas, hidratado, silíceo.
   - Entorno: rango térmico, aridez, hielo/permafrost, elevación del Sol (polos).
   - Operativo (solo Tierra): accesibilidad, protección legal, aislamiento.
2. **Normalizar** cada variable (percentiles/z-score dentro de cada cuerpo, porque las escalas absolutas no son comparables).
3. **Similitud ponderada** (distancia euclídea/coseno/Gower) con **pesos según el perfil de misión**:
   - 🚙 *Movilidad de rover* → terreno, rugosidad, granulometría.
   - 🧊 *ISRU / hielo* → hielo, frío, composición.
   - 🏠 *Hábitat / base* → térmico, aislamiento, cuevas.
   - 🔦 *Iluminación polo sur lunar* → elevación solar, sombras.
   - 🦠 *Astrobiología (Marte)* → química, aridez, UV.
4. **Validar** con los análogos conocidos (¿aparecen arriba?).
5. **Precalcular** todo en Python y exportar a JSON/GeoJSON → la UI calcula la similitud en el navegador (50k celdas × 10 variables es instantáneo). **Sin backend = menos riesgo el día de la demo.**

### Ideas complementarias / extras
| Idea | Esfuerzo | Valor |
|---|---|---|
| **Modo inverso:** pincho un sitio de la Tierra → a qué sitios de Luna/Marte se parece | Bajo (misma lógica) | Medio |
| **Atlas de análogos:** fichas estandarizadas de los análogos existentes (el enunciado dice que están "poco caracterizados") | Bajo | Alto |
| **Mapa de huecos:** zonas muy similares que nadie usa aún = análogos nuevos | Bajo (sale del motor) | **Muy alto** (es lo que pide el reto) |
| **Comparador visual** lado a lado a la misma escala (slider) | Medio | Alto para la demo |
| **Similitud por IA de imágenes/DEM** (embeddings de parches con un modelo preentrenado, p. ej. un *foundation model* geoespacial) | Alto | Alto pero arriesgado → *stretch goal* |
| Capa de **cuevas/tubos de lava** | Medio (datos dispersos) | Alto (originalidad) |
| Exportar informe PDF del sitio | Bajo | Medio |

### Propuesta de alcance
- **MVP (obligatorio):** 1 cuerpo (Marte *o* Luna) + 5–10 sitios objetivo predefinidos + 4–6 variables + mapa con top-N + ficha con radar.
- **Objetivo:** ambos cuerpos + perfiles de misión + validación con análogos conocidos + clic libre en cualquier punto.
- **Stretch:** similitud por IA, cuevas, modo inverso, comparador visual.

---

## 7. Posibles preguntas mañana (y respuestas preparadas)

### Del equipo / brainstorming
| Pregunta | Respuesta corta sugerida |
|---|---|
| ¿Luna, Marte o los dos? | Empezar por **uno** en el MVP (el que tenga mejores datos de los que nos den) y ampliar. |
| ¿Clic libre o sitios predefinidos? | MVP con sitios predefinidos (más controlado); clic libre si la rejilla global está lista. |
| ¿Qué variables? | Las que existan **en los dos cuerpos** a comparar. Si una variable solo existe en uno, no sirve para comparar. |
| ¿Cómo comparamos sensores y resoluciones distintas? | Remuestrear a una rejilla común y comparar **distribuciones/percentiles**, no valores absolutos. |
| ¿Stack? | Python para datos; UI web (React + MapLibre/Leaflet) o **Streamlit** si el equipo es solo Python. Decidir en el brainstorming. |
| ¿Backend? | Evitarlo en el MVP: precalcular y servir ficheros estáticos. |
| ¿Dónde guardamos datos pesados? | Fuera de git (Drive compartido). Ver [`data/README.md`](../data/README.md). |
| ¿Y si los datos que nos dan no encajan? | Plan B con datos globales gruesos ya conocidos (MOLA, TES, LOLA, WorldClim, Copernicus DEM). |

### De mentores / jurado
| Pregunta | Qué contestar |
|---|---|
| ¿Qué tiene de nuevo? | No es una lista estática: es un **motor reproducible** que propone análogos nuevos y explica *por qué* según el tipo de misión. |
| ¿Cómo sabéis que funciona? | **Validación** con análogos conocidos (Atacama, Haughton…) que el sistema recupera sin habérselo dicho. |
| ¿Qué datos de NASA usáis? | Enumerar (LOLA, MOLA, THEMIS, Diviner, ASTER/EMIT, MODIS…) y enlazarlos. |
| ¿Limitaciones? | Gravedad, atmósfera y radiación no son análogas; resolución gruesa; mineralogía aproximada. Decirlo da credibilidad. |
| ¿Quién lo usaría? | Planificadores de misiones (NASA/ESA), equipos de pruebas de rovers, universidades, agencias nacionales que buscan análogos cercanos. |
| ¿Escala? | Añadir un dataset = añadir una columna al vector de características. |

---

## 8. Entregables de Space Apps ⚠️ (confirmar en spaceappschallenge.org)

Habitualmente la entrega incluye:
- Título y resumen del proyecto.
- **Demo:** vídeo corto (~30 s) **o** presentación corta (hasta ~7 diapositivas).
- Enlace al repositorio / proyecto funcionando.
- Lista de **datos de NASA y otras agencias** usados.
- Declaración de **uso de IA**.

Criterios de evaluación habituales: **Impacto · Creatividad · Validez · Relevancia · Presentación**.

👉 Implica que **el vídeo/presentación no se deja para el final**: alguien es responsable desde el día 1 (ver roles).

---

## 9. Decisiones a tomar en el brainstorming

- [ ] Cuerpo(s) objetivo para el MVP: Luna / Marte / ambos
- [ ] Sitios objetivo concretos (5–10)
- [ ] Variables (4–6 por cuerpo) y datasets
- [ ] Método de similitud y perfiles de misión
- [ ] Stack de la UI (React+MapLibre vs Streamlit vs otro)
- [ ] Nombre del proyecto
- [ ] Asignación final de roles
- [ ] Hitos y horas de sincronización

Registrar cada decisión en [`docs/decisions/`](decisions/).
