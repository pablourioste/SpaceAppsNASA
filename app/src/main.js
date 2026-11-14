// Target body (Mars or Moon) on the left, Earth on the right.
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { createGlobe } from './globe.js';
import { loadSites } from './data.js';

const reliefBox = document.getElementById('relief');
const reliefLabel = reliefBox.closest('label');
const targetLabel = document.getElementById('target-label');
const buttons = document.querySelectorAll('.switch button');

const earth = createGlobe('earth', 'earth');
let target = null;
let sites = { targets: [], analogs: [] };

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
  }
  targetLabel.textContent = target.body.name;
  buttons.forEach((b) => b.classList.toggle('active', b.dataset.body === bodyKey));
  applyRelief();
}

buttons.forEach((b) => b.addEventListener('click', () => showTarget(b.dataset.body)));
reliefBox.addEventListener('change', applyRelief);

// Esc clears every selection: coordinate markers and highlighted sites on both globes
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  earth.clearSelection();
  target.clearSelection();
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
window.globes = {
  earth,
  get target() {
    return target;
  },
};
