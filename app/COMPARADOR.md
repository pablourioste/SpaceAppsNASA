# Comparador local: prototipo v1

Abrir app/index.html con doble clic. No requiere instalar librerias ni descargar
NASA. Toda la demo esta marcada como ficticia. No sobrescribe app/data/.

Seleccionar zona lunar, perfil o pesos, cobertura minima y un resultado.
El perfil Terreno compara pendiente y rugosidad; los otros pesos quedan a cero.
Exportar resultados guarda el indice, cobertura, pesos y tolerancias usados.

## Contrato provisional v1

El boton Descargar JSON de ejemplo entrega el formato completo. Incluye:
schema_version: 1, mock: true/false, variables (tolerancias positivas),
targets y earth (listas de fichas id, name, lat, lon, features).
Cada medida tiene value, status, unit, definition, scale_m y source.
status puede ser value, missing o lower_bound. null tambien indica ausencia.
Las definiciones deben codificar el metodo, agregacion, periodo y profundidad
cuando sean relevantes. Los identificadores deben acordarse entre equipos.

Solo se comparan valores exactos con iguales unidad, definicion y escala.
Los limites (p.ej. hielo >2.87 m) se muestran, pero no puntuan en esta version.
No introducir codigos -999 como valores ni interpretar desconocido como cero.
La rugosidad de la demo es RMS de pendiente en grados: validar la definicion
real PGDA antes de importar. Las tolerancias de la demo son supuestos.

La cobertura cuenta variables activas comparables, sin ponderarlas. Por defecto
exige todas. La similitud sigue la formula lineal de src/analogs/similarity.py,
pero aplica antes estos controles adicionales de comparabilidad.

Este contrato enriquece el formato existente app/data/, cuyos features son
numeros simples. No es compatible directamente: el equipo debe preparar un
adaptador con metadatos cientificos, sin inventar equivalencias.
No sustituye ni modifica el motor Python ni el generador existente.

## Integracion con el repositorio (14/11/2026)

Abrir app/comparador.html. Entrada separada de la aplicacion del equipo.
Se incluyen 9 objetivos lunares y 3000 celdas de los JSON de GitHub, revision
735025058b990c46b1808210eb7af4d85c6ce1da. TODOS siguen marcados DATOS FALSOS.
No se ha hecho pull, merge ni push; no se han reemplazado los JSON originales.

Para reconstruir desde las fichas locales actualizadas:

    python scripts/build_comparator_data.py

Genera app/repository-data.json y app/repository-data.js. Recarga el navegador.
Guarda hashes SHA-256 de las entradas y revision de procedencia. Para una
revision conocida usa --revision SHA. --input-dir permite otra carpeta.
La tabla muestra los 30 mejores; exportar resultados incluye todos los que
pasan el filtro. Los nombres de celdas conservan sus identificadores porque
el indice original no proporciona nombres de lugares.

La simulacion usa definiciones comunes y escala ficticia de 800 m solo para
probar la interfaz: no representa metadatos medidos en NASA.
Cuando desaparezca _aviso, el adaptador exige --metadata archivo.json.
Su estructura es {"moon": {VARIABLE: {"unit":..., "definition":...,
"source":..., "scale_m":...}}, "earth": {...}}.
El equipo debe definir estos metadatos. La definicion debe identificar metodo,
periodo y profundidad; las variables de terreno requieren escala positiva.
No convertir limites en numeros exactos: usar el contrato enriquecido v1
mediante importacion directa para status lower_bound. El adaptador de numeros
simples rechaza -999 y otros sentinelas negativos.

Pruebas sin dependencias externas:

    python -B tests/test_comparator_integration.py
