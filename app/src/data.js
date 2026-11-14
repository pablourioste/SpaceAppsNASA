// Loads the index written by the Python engine (app/data/, format in app/README.md).
const BASE = `${import.meta.env.BASE_URL}data/`;

async function getJson(name) {
  const res = await fetch(BASE + name);
  if (!res.ok) throw new Error(`Could not load data/${name} (HTTP ${res.status})`);
  return res.json();
}

/** Target sites (Moon/Mars) and known Earth analogs. */
export async function loadSites() {
  const [objetivos, analogos] = await Promise.all([
    getJson('objetivos.json'),
    getJson('analogos_conocidos.json'),
  ]);
  return {
    targets: objetivos.objetivos, // [{ id, name, body, lat, lon, type, features }]
    analogs: analogos.analogos, // [{ name, country, lat, lon, analog_of, environment, notes }]
    mock: Boolean(objetivos._aviso),
  };
}
