# app/ — interfaz de usuario (R6)

Stack **por decidir** en el brainstorming. Opciones:

| Opción | Pros | Contras |
|---|---|---|
| **React + Vite + MapLibre/Leaflet** | Máximo control y vistosidad; despliegue estático gratis (GitHub Pages/Vercel) | Requiere alguien cómodo con JS |
| **Streamlit + folium/pydeck** | Todo en Python, muy rápido de montar | Menos personalizable; interacción de mapas limitada |
| CesiumJS (globos 3D) | Muy impactante visualmente | Curva de aprendizaje |

Recomendación provisional: **sin backend**. La app lee los JSON de `outputs/results/` y calcula la similitud en el navegador.

Mapas base: teselas de **NASA Moon Trek / Mars Trek** para Luna y Marte; cualquier mapa base estándar para la Tierra.

Pantalla principal (borrador):
```
┌──────────────────────────┬──────────────────────────┐
│  LUNA / MARTE [toggle]   │  TIERRA                  │
│  (clic en sitio)         │  (mapa de calor + top-N) │
├──────────────────────────┴──────────────────────────┤
│ Perfil de misión: [Rover ▾]   Top-10 sitios  │ Ficha + radar │
└─────────────────────────────────────────────────────┘
```
