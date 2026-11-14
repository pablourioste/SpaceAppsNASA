# app/ — la app

## Qué hace

```
① INICIO     la Tierra, la Luna y Marte en 3D, con texturas reales de NASA
② FILTROS    ¿Qué quieres probar? [Ruedas ▾]   ¿Para dónde? [Marte · Jezero ▾]   [Buscar]
③ VUELO      la cámara va al objetivo (Marte, Jezero) y lo marca
④ RESULTADO  vuela a la Tierra, la colorea por índice (0–100) y baja sola al mejor match
⑤ FICHA      clic → índice + nota de cada variable (valor Marte vs. valor Tierra, con unidades y fuente)
              + bloque "no análogo" (gravedad, presión…) + validez de la prueba + fotos a la misma escala
⑥ AL REVÉS   clic en cualquier punto de la Tierra → a qué sitio de la Luna o Marte se parece más
```

**Regla:** primero que funcione lo básico (Tierra coloreada + clic → ficha). Después, vuelos y animaciones.

## De dónde saca los datos

- **Los matches:** SOLO de `app/data/`. La app **nunca** descarga datos científicos de NASA.
- **Los mapas y fotos:** en vivo desde los servidores de mapas (Worldview/GIBS para la Tierra, Moon Trek / Mars Trek para la Luna y Marte). Son públicos y no piden cuenta [verificar URLs de teselas].
- **Sin servidor propio:** es una web estática (GitHub Pages / Vercel).

## Formato de `app/data/` (el contrato entre el motor y la app)

Lo escribe [`src/analogs/export.py`](../src/analogs/export.py). Para tener ya datos falsos: `python scripts/make_mock_data.py`.

| Fichero | Contenido |
|---|---|
| `config.json` | `variables` (unidad, tolerancia, tipo), `pruebas` (pesos + frase de validez), `bodies` (gravedad, presión, día) y `operability` |
| `objetivos.json` | `{"objetivos": [{id, name, body, lat, lon, type, features: {slope_deg: …, t_mean_K: …}}]}` |
| `tierra.json` | `{"n_cells": N, "columns": {"cell_id": […], "lat": […], "lon": […], "slope_deg": […], …}}`, una lista por columna, `null` = sin dato |
| `analogos_conocidos.json` | `{"analogos": [{name, country, lat, lon, analog_of, environment, notes}]}` |

Si llevan `"_aviso": "DATOS FALSOS…"`, la app debe enseñarlo bien visible.

## La fórmula (tiene que ser IDÉNTICA a `src/analogs/similarity.py`)

```
nota_k  = max(0, 1 − |objetivo_k − tierra_k| / tolerancia_k)      (numérica)
nota_k  = matriz[objetivo_k][tierra_k], o igual → 1 / distinto → 0   (categórica)
índice  = 100 · Σ peso_k · nota_k / Σ peso_k     (solo variables con dato en los dos)
```

Comprobación: con el ejemplo de [`tests/test_similarity.py`](../tests/test_similarity.py), la versión de la app tiene que dar 37,5 / 82,5 / 77,5.

## Opciones de librería (decidir el sábado)

| Opción | Pros | Contras |
|---|---|---|
| **globe.gl** (three.js) | Globo 3D en pocas líneas; texturas propias (Luna, Marte); vuelo de cámara con una llamada [verificar API] | Menos control que Cesium |
| **CesiumJS** | Muy potente, vuelos de cámara, muchos formatos | Cuesta más aprenderla |
| **React + MapLibre** | Control total, mapas 2D/globo | Hace falta alguien cómodo con JS |
| **Streamlit + pydeck** | Todo en Python, rápido | Menos vistoso; animaciones limitadas |

Texturas: NASA Blue Marble (Tierra), mosaicos de LRO (Luna) y Viking/MOLA (Marte) [verificar fuentes y licencias].
