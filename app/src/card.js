// The card panel: shows the values of one H3 cell (ROADMAP 4.9).
import { formatLatLon } from './coords.js';

// Sections of the card and the columns they show (columns not in the grid are skipped)
const SECTIONS = [
  ['Terrain', ['elevation_m', 'slope_deg', 'roughness_deg', 'mola_measured_frac', 'lola_measured_frac',
    'rock_abundance_pct']],
  ['Climate & light', ['t_mean_K', 't_max_K', 't_min_K', 't_night_K', 'dust_aod', 'p_surf_Pa',
    'sun_elev_max_deg', 'psr_frac']],
  ['Ice & composition', ['ice_depth_m', 'ice_frac_1m', 'grs_h2o_wt_pct', 'ns_epithermal_cps', 'grs_cl_wt_pct',
    'thermal_inertia_day_SI', 'feo_wt_pct', 'tio2_wt_pct', 'silica_wt_pct', 'th_ppm']],
  ['Subsurface', ['caves', 'pit_dist_km']],
];

// Where each value's source comes from (docs/07, "Where the source of each value comes from"):
//   - index.json, per column: `source` (full text, tooltip) and `short_source` (tag on the card);
//   - if the source varies per cell, the column has `source_column` = a code column in the binary,
//     and that code column has `codes` = {code: tag}. E.g. ice_depth_m → ice_depth_source (1/2/3).
// Nothing about sources is hard-coded here.

const SHORT = {
  elevation_m: 'Elevation',
  slope_deg: 'Slope',
  roughness_deg: 'Roughness',
  mola_measured_frac: 'Laser coverage (QC)',
  t_mean_K: 'Mean temperature',
  t_max_K: 'Max temperature',
  t_night_K: 'Night temperature',
  dust_aod: 'Dust (optical depth)',
  p_surf_Pa: 'Surface pressure',
  sun_elev_max_deg: 'Max Sun elevation',
  ice_depth_m: 'Water ice',
  grs_h2o_wt_pct: 'Hydrogen (as H₂O)',
  grs_cl_wt_pct: 'Chlorine',
  ns_epithermal_cps: 'Neutrons (low = more H)',
  thermal_inertia_day_SI: 'Thermal inertia',
  // Moon
  lola_measured_frac: 'Laser coverage (QC)',
  t_min_K: 'Min temperature',
  psr_frac: 'Permanent shadow',
  ice_frac_1m: 'Ice within 1 m (area)',
  feo_wt_pct: 'Iron (FeO)',
  tio2_wt_pct: 'Titanium (TiO₂)',
  silica_wt_pct: 'Silica (SiO₂)',
  th_ppm: 'Thorium',
  rock_abundance_pct: 'Rocks',
  caves: 'Cave entrance (pit)',
  pit_dist_km: 'Nearest known pit',
};

const ICE_CLASSES = { 0.5: 'within 1 m', 3: '1–5 m deep', 5: 'deeper than 5 m', 10: 'none (top 5 m)' };

function decimals(scale) {
  return scale >= 1 ? 0 : Math.min(3, Math.ceil(-Math.log10(scale)));
}

const tag = (text) => (text ? ` <span class="tag">${text}</span>` : '');

/** Short source of a column's value in this cell: per-cell code if any, else the fixed tag. */
function sourceOf(col, values, cols) {
  if (col.source_column) {
    const codeCol = cols[col.source_column];
    return codeCol?.codes?.[String(values[col.source_column])] ?? '';
  }
  return col.short_source ?? '';
}

/** { text, src }: the value and its short source (no source when there is no value). */
function formatValue(col, v, values, cols) {
  const text = valueText(col, v, values, cols);
  if (text.startsWith('<span class="nodata">')) return { text, src: '' };
  let src = sourceOf(col, values, cols);
  // "ice-rich" fallback for hydrogen: it comes from the ice value, so it takes the ice's source
  if (col.name === 'grs_h2o_wt_pct' && !Number.isFinite(v) && cols.ice_depth_m) {
    src = sourceOf(cols.ice_depth_m, values, cols);
  }
  return { text, src };
}

function valueText(col, v, values, cols) {
  const iceSrc = cols.ice_depth_m ? sourceOf(cols.ice_depth_m, values, cols) : '';
  const moon = Boolean(cols.psr_frac); // only the Moon grid has a permanent-shadow column
  if (moon) {
    const lat = Math.abs(values._lat);
    if (col.name === 'ice_depth_m') {
      if (!Number.isFinite(v)) return '<span class="nodata">no data (no product for 60–80° or the north pole)</span>';
      if (v === 0) return 'stable at the surface';
      if (v >= 10) return iceSrc === 'assumed' ? 'none (not stable away from the poles)' : 'none within ~2.9 m';
      return `${v.toFixed(2)} m deep`;
    }
    if (col.name === 'sun_elev_max_deg' && !Number.isFinite(v) && lat >= 80) {
      return '<span class="nodata">relief decides the light here: see permanent shadow</span>';
    }
    if ((col.name === 'psr_frac' || col.name === 'ice_frac_1m') && !Number.isFinite(v)) {
      return '<span class="nodata">only mapped at 80–90° S</span>';
    }
    if (col.name === 'rock_abundance_pct' && !Number.isFinite(v)) {
      return '<span class="nodata">not mapped beyond ±60°</span>';
    }
    if (col.name === 'psr_frac' || col.name === 'ice_frac_1m') return `${Math.round(v * 100)} % of the cell`;
    if (col.name === 'caves' && Number.isFinite(v)) return v >= 1 ? 'yes' : 'none known';
  }
  if (col.name === 'ice_depth_m') {
    if (!Number.isFinite(v)) {
      return iceSrc === 'neutrons' ? 'not detected in top ~1 m' : '<span class="nodata">no data</span>';
    }
    return ICE_CLASSES[v] ?? `${v} m`;
  }
  if (col.name === 'grs_h2o_wt_pct' && !Number.isFinite(v)) {
    // GRS element maps stop at ~±50°: say what the neutrons say instead of inventing a wt%
    if (values.ice_depth_m === 0.5 && iceSrc) return 'ice-rich';
    return '<span class="nodata">no wt% here (see neutrons)</span>';
  }
  if (!Number.isFinite(v) && Math.abs(values._lat) > 87) {
    if (col.name === 'slope_deg' || col.name === 'roughness_deg' || col.name === 'mola_measured_frac') {
      return '<span class="nodata">not measured (MGS never flew over |lat| &gt; 87°)</span>';
    }
    if (col.name === 'thermal_inertia_day_SI') return '<span class="nodata">not measured (TES coverage ends ~87°)</span>';
  }
  if (!Number.isFinite(v) && col.name === 'elevation_m' && Math.abs(values._lat) > 88) {
    return '<span class="nodata">polar map, other height reference (not shown)</span>';
  }
  if (!Number.isFinite(v)) return '<span class="nodata">no data</span>';
  if (col.name.endsWith('_measured_frac')) return `${Math.round(v * 100)} % measured`;
  const shown = col.short_unit ?? col.unit;   // short unit from index.json when the full one is long
  const unit = shown ? ` ${shown}` : '';
  return `${v.toFixed(decimals(col.scale))}${unit}`;
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

export function createCardPanel(el, { onClose } = {}) {
  el.addEventListener('click', (e) => {
    if (e.target.closest('[data-close]')) onClose?.();
  });

  return {
    loading(title, lat, lon) {
      el.hidden = false;
      el.innerHTML = `<header><h2>${esc(title)}</h2><button data-close aria-label="Close">×</button></header>
        <p class="where">${formatLatLon({ lat, lon })}</p><p class="muted">Loading the card…</p>`;
    },
    message(title, text) {
      el.hidden = false;
      el.innerHTML = `<header><h2>${esc(title)}</h2><button data-close aria-label="Close">×</button></header>
        <p class="muted">${esc(text)}</p>`;
    },
    /** card = CardGrid.cardAt() result */
    show(title, lat, lon, card) {
      const cols = Object.fromEntries(card.columns.map((c) => [c.name, c]));
      const values = { ...card.values, _lat: lat };
      const sections = SECTIONS.map(([name, keys]) => {
        const rows = keys.filter((k) => cols[k]).map((k) => {
          const col = cols[k];
          const { text, src } = formatValue(col, values[k], values, cols);
          return `<dt title="${esc(col.label)}">${SHORT[k] ?? esc(col.label)}</dt>
                  <dd title="${esc(col.unit ? `Unit: ${col.unit} · ` : '')}Source: ${esc(col.source)}">${text}</dd>
                  <dd class="src" title="Source: ${esc(col.source)}">${src ? tag(src) : ''}</dd>`;
        }).join('');
        return rows ? `<section><h3>${name}</h3><dl>${rows}</dl></section>` : '';
      }).join('');
      el.hidden = false;
      el.innerHTML = `<header><h2>${esc(title)}</h2><button data-close aria-label="Close">×</button></header>
        <p class="where">${formatLatLon({ lat, lon })} · cell <code>${card.h3}</code> (~${card.cellSizeKm ?? 9} km)</p>
        ${sections}
        <footer>Earth match: next step — needs the Earth card grid in the app (ROADMAP 3.16, Earth).
        Hover a value to see its source.</footer>`;
    },
    hide() {
      el.hidden = true;
      el.innerHTML = '';
    },
  };
}
