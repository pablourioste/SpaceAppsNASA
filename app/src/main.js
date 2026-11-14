// Target body (Mars or Moon) on the left, Earth on the right.
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { createGlobe } from './globe.js';
import { loadSites } from './data.js';
import { CardGrid } from './grid.js';
import { createCardPanel } from './card.js';
import { cellToBoundary, cellToLatLng } from 'h3-js';
import { latLonToCartesian } from './coords.js';

const reliefBox = document.getElementById('relief');
const reliefLabel = reliefBox.closest('label');
const targetLabel = document.getElementById('target-label');
const buttons = document.querySelectorAll('.switch button');

const earth = createGlobe('earth', 'earth');
let target = null;
let sites = { targets: [], analogs: [] };

// --- 4.9 Click any point of the target body → card of its H3 cell ---
// Planet-wide card grids available in app/data/ (the Moon comes with ROADMAP 3.7 + 3.16)
const GRIDS = { mars: new CardGrid('marte') };
const card = createCardPanel(document.getElementById('card'), { onClose: clearAll });
let cardRequest = 0; // ignore answers to older clicks

async function showCardAt(lat, lon, title) {
  const request = ++cardRequest;
  const grid = GRIDS[target.key];
  if (!grid) {
    target.clearCell();
    card.message(title, `No card grid for the ${target.body.name} yet (ROADMAP 3.7 + 3.16).`);
    return;
  }
  card.loading(title, lat, lon);
  try {
    const c = await grid.cardAt(lat, lon);
    if (request !== cardRequest) return;
    if (!c) {
      card.message(title, 'No data for this cell.');
      return;
    }
    target.showCell(c.h3);
    card.show(title, lat, lon, c);
    frameCell(c.h3);
  } catch (err) {
    console.error(err);
    if (request === cardRequest) card.message(title, `Could not load the card: ${err.message}`);
  }
}

const CELL_FILL = 0.55; // the hexagon spans ~55 % of the free part of the globe

/**
 * Fly the camera straight down onto an H3 cell, zoomed so the hexagon is well framed in the part
 * of the globe the card leaves free (left of it on wide screens, above it on phones).
 */
function frameCell(h3) {
  const { viewer } = target;
  const ell = target.body.ellipsoid;
  const latType = target.body.latitudeType; // H3 lat/lon use the body's convention (planetocentric on Mars)
  const toXYZ = (la, lo, h = 0) => latLonToCartesian(la, lo, ell, latType, h);
  const [lat, lon] = cellToLatLng(h3);
  // Hexagon size on the ground: largest centre-to-vertex distance, ×2
  const centre = toXYZ(lat, lon);
  const radius = Math.max(...cellToBoundary(h3).map(([la, lo]) => Cesium.Cartesian3.distance(centre, toXYZ(la, lo))));
  const diameter = 2 * radius;

  const canvas = viewer.canvas.getBoundingClientRect();
  const panel = document.getElementById('card').getBoundingClientRect();
  const narrow = panel.left - canvas.left < 120;
  const free = narrow
    ? { w: canvas.width, h: Math.max(80, panel.top - canvas.top), x: canvas.width / 2 }
    : { w: Math.max(80, panel.left - canvas.left), h: canvas.height, x: (panel.left - canvas.left) / 2 };
  free.y = narrow ? free.h / 2 : canvas.height / 2;

  // Camera height so that `diameter` metres cover CELL_FILL of the smaller free dimension
  const mPerPx = diameter / (CELL_FILL * Math.min(free.w, free.h));
  const height = (mPerPx * canvas.height) / (2 * Math.tan(viewer.camera.frustum.fovy / 2));

  // Shift the camera so the cell lands in the middle of the free part, not under the card
  const dx = (canvas.width / 2 - free.x) * mPerPx;   // metres east
  const dy = (free.y - canvas.height / 2) * mPerPx;  // metres north
  const R = ell.maximumRadius;
  const camLon = lon + Cesium.Math.toDegrees(dx / (R * Math.max(0.05, Math.cos(Cesium.Math.toRadians(lat)))));
  const camLat = Math.max(-89.9, Math.min(89.9, lat + Cesium.Math.toDegrees(dy / R)));
  viewer.camera.flyTo({
    // same latitude convention as the cell, raised along the surface normal → looking straight down
    destination: toXYZ(camLat, camLon, height),
    orientation: { heading: 0, pitch: -Cesium.Math.PI_OVER_TWO, roll: 0 },
    duration: 1.2,
  });
}

function clearAll() {
  cardRequest++;
  card.hide();
  earth.clearSelection();
  target.clearSelection();
}

function applyRelief() {
  earth.setRelief(reliefBox.checked);
  target.setRelief(reliefBox.checked);
  reliefLabel.classList.toggle('disabled', !target.hasRelief);
  reliefLabel.title = target.hasRelief ? '' : `No relief layer for the ${target.body.name} yet`;
}

function showTargetSites() {
  target.setSites(sites.targets.filter((s) => s.body === target.key), 'target');
}

function showTarget(bodyKey) {
  if (!target || target.key !== bodyKey) {
    target?.destroy();
    target = { ...createGlobe('target', bodyKey), key: bodyKey };
    showTargetSites();
    clearAll();
    target.onPick(({ lat, lon }) => showCardAt(lat, lon, `${target.body.name} · selected point`));
    target.onSiteSelect((site) => showCardAt(site.lat, site.lon, site.name));
  }
  targetLabel.textContent = target.body.name;
  buttons.forEach((b) => b.classList.toggle('active', b.dataset.body === bodyKey));
  applyRelief();
}

buttons.forEach((b) => b.addEventListener('click', () => showTarget(b.dataset.body)));
reliefBox.addEventListener('change', applyRelief);

// Esc clears every selection: coordinate markers, highlighted sites, cell outline and card
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') clearAll();
});

showTarget('mars');

loadSites()
  .then((data) => {
    sites = data;
    showTargetSites();
    earth.setSites(
      data.analogs.map((a) => ({ ...a, id: a.name, subtitle: a.country })),
      'analog',
    );
  })
  .catch((err) => console.error(err));

// For debugging from the browser console
window.Cesium = Cesium;
window.CardGrid = CardGrid;
window.showCardAt = (lat, lon, title = 'debug') => showCardAt(lat, lon, title);
window.globes = {
  earth,
  get target() {
    return target;
  },
};
