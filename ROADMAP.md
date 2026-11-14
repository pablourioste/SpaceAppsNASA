# Roadmap: phases and tasks

> Project tracking list. Tick each task when it is done: `- [ ]` → `- [x]`.
> Last update: 2026-11-14.

**Legend:** `app/` = the web app (Vite + CesiumJS) · `src/analogs/` = the engine and Python preprocessing · `app/data/` = the index the app reads (format in [`app/README.md`](app/README.md)).

**Progress:** 29 / 62 tasks done.

> **Main goal (decision 007, proposal):** click **any point** of the Moon or Mars → the app finds the most similar place on Earth and flies there. So Mars and the Moon need a **global card grid**, not only the 21 target sites (tasks 3.4b, 3.5, 3.7, 3.16, 4.9).

---

## Phase 0 · Setup

- [x] **0.1** Create the GitHub repository and folder structure (`app/`, `src/`, `data/`, `docs/`…).
- [x] **0.2** Create the web project in `app/` with Vite 6 + CesiumJS 1.147. Checked in the browser: the globe loads without errors and reads `app/data/`.
- [x] **0.3** Automatic deployment to GitHub Pages: workflow `.github/workflows/deploy-app.yml` (`npm ci` + `npm run build` in `app/` → publishes `app/dist/`). Checked locally.
- [x] **0.4** Fix the data format between the engine and the app: `config.json`, `objetivos.json`, `tierra.json`, `analogos_conocidos.json` (see `app/README.md`).
- [x] **0.5** Choose the grid: H3 hexagons at resolution 4 on Earth and a ~10 km "footprint" at the Moon and Mars target sites (see `docs/03_enfoque.md`, marked as an assumption).
- [x] **0.6** Mock data so the app can move ahead: `python scripts/make_mock_data.py` → `app/data/` (flagged with `"_aviso"`).
- [x] **0.7** Set up the Python environment (`.venv` + `pip install -r requirements.txt`) and check that `python -m pytest` passes: 8 passed. If `pip` fails with an SSL certificate error, add `--use-feature=truststore`.
- [ ] **0.8** Enable GitHub Pages (Settings → Pages → Source: "GitHub Actions"; the repository owner must do this), merge the branch into `main` and check that the site is published.

## Phase 1 · The three globes (`app/`)

- [x] **1.1** **Earth** viewer with NASA GIBS imagery (Blue Marble, Web Mercator, max level 8).
- [x] **1.2** **Mars** viewer with `Ellipsoid.MARS` and Mars Trek tiles (`Mars_Viking_MDIM21_ClrMosaic_global_232m`).
- [x] **1.3** **Moon** viewer with `Ellipsoid.MOON` and Moon Trek tiles (`LRO_WAC_Mosaic_Global_303ppd_v02`).
- [x] **1.4** Turn off the atmosphere, fog, and Earth's Sun/Moon in the Mars and Moon viewers (stars kept).
- [x] **1.5** Screen layout: target (Moon or Mars) on the left and Earth on the right (stacked on narrow screens), with a button to switch between the Moon and Mars.
- [x] **1.6** Zoom and poles checked. Deepest level Trek actually serves: Mars 7 (~330 m/px), Moon 8; beyond that Cesium upsamples the last tile. Earth's north pole: small artifact above 85° (Web Mercator limit).
- [x] **1.7** Relief layer with a toggle: MOLA colour hillshade (Mars), LOLA colour hillshade v6 (Moon; Trek serves it as PNG) and ASTER GDEM colour shaded relief (Earth).
- [x] **1.8** High-resolution imagery drawn automatically when zooming in: MRO CTX global mosaic for Mars (~5 m/px, greyscale, Caltech Murray Lab/Esri, listed by Mars Trek; up to level 12) and Sentinel-2 cloudless 2016 for Earth (~10 m/px, EOX, CC BY 4.0; up to level 14). The Moon stays at LRO WAC (~100 m/px).

## Phase 2 · Interaction and coordinates (`app/`)

- [x] **2.1** Click on the globe → latitude and longitude for each body with its own ellipsoid (`app/src/coords.js`). Mars and Moon use **planetocentric** latitude (as PDS products do); Earth uses **geodetic** WGS84 latitude. Longitude −180…180 east. Checked: Jezero (Mars), Barcelona (Earth), Tycho (Moon).
- [x] **2.2** Marker with a coordinate label at the clicked point (one per globe; `setMarker`, `clearMarker` and `onPick` exposed for phase 4).
- [x] **2.3** Live coordinate readout under the mouse (bottom-right of each globe).
- [x] **2.4** `globe.flyTo(lat, lon, height?)` animates the camera above a point (default height per body: Earth 800 km, Mars 600 km, Moon 400 km); returns a Promise.
- [x] **2.5** Target sites from `objetivos.json` drawn on the Moon (9) and Mars (12) as yellow named points. Click → highlight + fly to it (`onSiteSelect` exposed for phase 4). Sites on the far side are hidden.
- [x] **2.6** Known analogs from `analogos_conocidos.json` (20) drawn on Earth as green named points, same behaviour.
- [x] **2.7** `Esc` clears every selection on both globes (coordinate markers and highlighted sites).

## Phase 3 · Data and engine (`src/analogs/`, in parallel with phases 1 and 2)

### 3A · Mars
- [x] **3.1** Download MOLA MEGDR (16 px/deg) → `data/raw/mars/mola_megdr_16ppd/`. Topography 5760×2880, int16 big-endian, −8177…21171 m (checked).
- [x] **3.2** Download the TES thermal inertia maps → `data/raw/mars/tes_thermal_inertia/`. Day + night 7200×3600 (20 px/deg), int16 big-endian, 0…4999 (0 = no data) + interpolation masks.
- [x] **3.3** Download GRS → `data/raw/mars/grs_special/` (NS neutron flux on a 0.5° grid, −99.999 = no data) and `data/raw/mars/grs_elements/` (H₂O, Cl, Fe, Si, K, Th on a 5°×5° grid, 9999.999 = no data).
  Run: `python scripts/download_data.py` (safe to re-run; skips files already downloaded).
- [x] **3.4** Download surface temperature and dust opacity: MGS TES IR retrievals for Mars Year 26 (Montabone et al., PDS Atmospheres) → `data/raw/mars/tes_atmos_my26/`. One product gives column dust OD, water-ice OD, surface temperature and surface pressure: 5.29 M retrievals over the full year (Ls 0–360). **All retrievals are daytime (~14 h)**, so they give `t_max_K` and `dust_aod` but not a night or diurnal-mean temperature (`t_mean_K` needs another source, see 3.5). MY26 chosen because MY25 had a global dust storm. ~490 MB; the server is slow (~0.1–0.6 MB/s). `python scripts/download_data.py tes_atmos` (resumable).
- [x] **3.4b** ✅ Done 2026-11-14: all 16 tiles (32 files, 2.9 GB) + both polar maps. Download the **10 remaining MOLA 128 px/deg tiles** (16 in total, ~3.1 GB with the shots-per-cell tiles) so slope/roughness exist for all of Mars (decision 007). Better outside OneDrive with `ANALOGS_DATA_DIR`. *(Moved here from old task 5.6.)* `python scripts/download_data.py mola128_all`.
  **Poles:** MOLA polar MEGDRs at 128 px/deg (460 m/px, polar stereographic, 37.45°→90° N and S; ~630 MB with the shots-per-cell maps) → `data/raw/mars/mola_megdr_polar128/` (`python scripts/download_data.py mola_polar`). Same baseline as the tiles; use them for |lat| > 88° (and to cross-check the overlap). ⚠️ The polar topography is stored as **unsigned** 16-bit (`MSB_UNSIGNED_INTEGER`) with a scale and offset (from the label): **topography (m) = stored × 0.25 − 8000**, relative to a 3,396,000 m sphere (not the areoid, unlike the tiles).
- [x] **3.5** Build the **Mars card grid for the whole planet** (decision 007) and the cards of the 12 Mars target sites: slope, roughness, thermal inertia, hydrogen/ice, temperature and dust.
  ✅ **Done 2026-11-14:** `python scripts/build_mars_grid.py` (code in `src/analogs/mars_grid.py`, ~18 min) → `data/processed/mars_h3r5.parquet` (2,016,842 H3 res-5 cells, 127 MB) + `data/processed/fichas_objetivos_mars.parquet` (12 sites). Quick-look maps of every variable: `outputs/maps/mars_h3r5_quicklook.png` (Tharsis, Hellas, Valles Marineris, dusty low-TI regions, polar ice and Arabia H₂O all where expected).
  Coverage: slope/roughness/K/Th/neutrons/sun 100 %, TES TI 99.9 %, temperatures and dust ~99.2–99.9 %, SWIM 86.8 % (±60°), GRS H₂O/Cl/Fe/Si 78.7 % (±~50°).
  Fixes after review: SWIM ice threshold raised from 0 to **0.25** (with 0, 43 % of the "ice ≤ 1 m" cells were equatorial; now 1.6 %; Arcadia 0.5 m, Viking 2 3 m, equatorial sites "no ice"); Th is in **ppm** (`grs_th_ppm`).
  **Open points:** (1) site card = card of the H3 cell that contains the site (~9 km), not a footprint centred on it — small difference at this scale; (2) `t_mean_K` looks blocky/noisy at 5° (few MCS night samples per cell): smooth it (e.g. 10° bins or a Gaussian filter) if it matters; (3) the "3 m" ice class has 13.5 % of its cells at |lat| < 30° (radar-based layer; e.g. Medusae Fossae) — Science to review; (4) "no ice" is stored as 10 m (`NO_ICE_DEPTH_M`, assumption).
  - Grid (decided): **H3 resolution 5** (~9 km hexagons on Mars and the Moon ≈ the ~10 km footprint of decision 006; ~2 M cells per body, H3 treats the body as a sphere with planetocentric lat/lon) → one row per cell with every variable. Exported **split by the 122 H3 base cells** so the app only downloads the region that was clicked (~600 KB each). Two clicks less than ~9 km apart give the same answer: that is the scale the data support (GRS is ~300 km, TES/MCS atmosphere tens of km). Target sites: their own ~10 km footprint card, as planned.
  - Coverage gaps are fine: a variable missing in a cell (SWIM beyond ±60°, GRS elements beyond ~±45°) is left empty and the formula skips it.
  - **Method (decided, 2026-11-14) — raster/points → H3 cell.** Going from fine pixels to ~9 km cells is a **low-pass** (averaging, avoids aliasing); a **high-pass** is used **only for roughness**. Every average is **area-weighted**. The same method must be used for Earth (3.9–3.12) so both sides are comparable (decision 006).

    | Variable | Source | Method |
    |---|---|---|
    | `slope_deg` | MOLA 128 ppd (~463 m) | slope at every pixel (true metric spacing per latitude) → **weighted median** inside the hexagon, weight = pixel area (∝ cos lat; polar maps: projection scale factor) |
    | `roughness_deg` | MOLA 128 ppd | **high-pass**: subtract a plane fitted to the hexagon's elevations (removes the regional tilt) → slope of the residual surface → **weighted RMS** inside the hexagon |
    | `mola_measured_frac` (QC) | MOLA `megc` | area-weighted fraction of pixels with ≥ 1 laser shot |
    | `thermal_inertia_{day,night}_SI` | TES TI (~3 km) | **area-of-intersection weighted mean** (only ~9 pixels per hexagon: pixel-centre assignment is not accurate enough; subdivide pixels or intersect polygons); interpolated pixels (mask = 0) dropped when measured ones exist |
    | `ice_depth_m` | SWIM 2.0 (~3 km) | area-of-intersection weighted mean of each consistency map → depth class (0.5 / 3 / 5 m / no ice) |
    | `grs_*`, `ns_epithermal_cps` | GRS 5° / 0.5° | value of the coarse cell that contains the hexagon centre (cells ≫ 9 km) |
    | `t_max_K`, `dust_aod` | TES MY26 (points, day) | bin to 5° cells (mean, P95 for t_max) → value of the 5° cell that contains the hexagon centre |
    | `t_mean_K` | TES day + MCS night | (5° day mean + 5° night mean) / 2, same lookup |
    | `sun_elev_max_deg` | geometry | formula with the hexagon centre latitude |

    Implementation notes: assign each pixel to its H3 cell (`h3` vectorised on pixel centres) and `groupby`; process MOLA **tile by tile** (16 tiles + 2 polar maps, ~10⁹ pixels in total) to fit in memory; cells that straddle two tiles are merged after accumulating weighted sums.
  *Draft code in `src/analogs/mars.py` + `scripts/build_mars_features.py` (readers checked on MOLA, TES TI and GRS; written for the sites only, not run end-to-end yet; extend to the grid).*
  **Slope and roughness at ~463 m (decided):** use MOLA MEGDR 128 px/deg instead of the 16 px/deg global map (3.7 km). The ~10 km site footprint then holds ~20×20 pixels instead of 3×3, and the baseline matches the Moon (LOLA `ldem_64`, ~474 m) and Earth (Copernicus DEM resampled to ~460 m), as decision 006 requires. Tiles in `data/raw/mars/mola_megdr_128ppd/` (`python scripts/download_data.py mola128`; today only the 6 tiles that contain a target site, the rest in 3.4b).
  > ⚠️ **Warning: interpolated cells.** MOLA measures along the spacecraft ground tracks; near the equator the gaps between tracks can be several km wide, so at 128 px/deg many cells have **no laser shot and are interpolated**. In those cells the slope comes out **smoother than reality**. For every site, use the shots-per-cell tile (`megc…hb`) to report the **fraction of measured cells** in the footprint, store it as a QC column (e.g. `mola_measured_frac`) and flag sites where it is low (threshold to decide).
  > **Measured so far (2026-11-14):** at the 12 Mars sites only **15–46 %** of the 128 px/deg cells in the footprint have a laser shot (Viking 1 15 %, Arcadia 19 %, Jezero 46 %). So a fixed "< 50 %" threshold would flag every site: report the fraction on the card instead of discarding sites, and consider computing slope only from measured cells.
  **`t_mean_K` (decided, data downloaded):** MRO MCS surface temperature, day (~15 h) and night (~03 h), Mars Year 31 (2011-09-13 → 2013-07-30), one Earth day in 10, two 4-hour files per day → `data/raw/mars/mcs_tsurf_my31/` (only the T_surf columns are kept, ~1 GB of source files reduced to a few MB; source URLs in MANIFEST). Reading notes: `LTST` is a **fraction of a sol** (0.0–0.1 = night, 0.5–0.6 = day), `T_surf = -9999` = no retrieval (drop). Bin day and night separately (e.g. 5° cells) and take `t_mean_K = (mean day + mean night) / 2`.
  > **Checked (2026-11-14):** 131 of 138 files (7 missing: MCS has **no data at all from 2012-08-07 to 2012-09-07**; nearby days used where possible), 4.2 MB, 40,151 valid T_surf (20 k night, 19 k day), every 5° cell has data but only ~7–8 samples per cell per day/night, and some cells have no day sample (e.g. Gale). Values make sense (Jezero ~224 K, Arcadia ~194 K, Phoenix ~168 K). **Suggested:** day mean from TES MY26 (millions of retrievals) + night mean from MCS, both binned at 5° (or smoothed), `t_mean_K = (day + night) / 2`.
  **`ice_depth_m` (decided, data downloaded):** SWIM 2.0 combined ice-consistency maps (−1 = inconsistent with ice … +1 = consistent) for 0–1 m, 1–5 m and >5 m → `data/raw/mars/swim2_ice/`. GeoTIFF, Mars2000 equicylindrical, ~3 km pixels, **±60° latitude only**. Proposed rule: depth = 0.5 m if CI[0–1 m] > 0, else 3 m if CI[1–5 m] > 0, else 5 m if CI[>5 m] > 0, else "no ice" (NaN or large value, to decide). Checked at the sites: Arcadia +0.43 (shallow ice), Oxia −0.50 and Viking 1 −0.45 (no ice). **Phoenix (68° N) is outside SWIM**: use GRS neutrons plus the ice the lander itself found a few cm down.
  **To decide when doing 3.5:**
  - GRS element maps have no data north of ~45° (Arcadia, Phoenix, Viking 2): use the NS epithermal neutron flux there for ice/hydrogen.
  - Whether to add the Mars-only extras (thermal inertia, GRS H₂O/Cl, surface pressure) to `configs/variables.yaml`.

### 3B · Moon
- [ ] **3.6** Download Diviner PRP (temperature, ice depth) and LOLA.
- [ ] **3.7** Build the **Moon card grid for the whole Moon** (same grid as Mars: H3 res 5, ~9 km, split by base cell; decision 007) and the cards of the 9 Moon target sites. Marc's kit covers the globe (Diviner GCP, LOLA `ldem_64`, Lunar Prospector) plus the south pole in detail (Diviner PRP, PGDA): see `docs/06_datos_luna.md`.

### 3C · Earth
- [ ] **3.8** Build the H3 resolution-4 grid for Earth (land only).
- [ ] **3.9** Copernicus DEM → slope and roughness per hexagon (same baseline as Mars and the Moon).
- [ ] **3.10** MODIS LST and albedo → temperature and apparent thermal inertia (ATI).
- [ ] **3.11** SMAP and JAXA snow/ice → soil moisture and ice.
- [ ] **3.12** MODIS AOD → dust and aerosols.

### 3D · Engine and export
- [x] **3.13** Similarity formula in `src/analogs/similarity.py` with tests in `tests/test_similarity.py`.
- [ ] **3.14** Fill `configs/variables.yaml` (units, tolerances) and `configs/pruebas.yaml` (weights per test type) with real values.
- [ ] **3.15** Put every variable on the same scale on all bodies: compute it at the ~10 km site footprint (decision 006) and compare in physical units with tolerances (decision 003, not percentiles or z-scores per body).
- [ ] **3.16** Export the real index to `app/data/` with `python scripts/run_pipeline.py`.
  ✅ **Mars part done (2026-11-14):** `python scripts/export_mars_web.py` → `app/data/marte/` (compact **binary**: quantized u1/u2 columns, gzip, one file per H3 base cell; 2,016,842 cells, 14 variables, **11 MB**, 68–106 KB per region) + real cards of the 12 Mars sites in `app/data/marte/objetivos.json` (kept out of the mock `objetivos.json`, which `build_comparator_data.py` requires to be all-mock or all-real). Reader `app/src/grid.js` (`CardGrid`, uses `h3-js`). Checked: `scripts/check_grid_binary.py` (all columns within scale/2, 0 no-data mismatches; 47 dust cells clipped at 2.54) and in the browser (same cells, order and values as Python). **Format + recipe for Earth and Moon: [`docs/07_card_grid_binary_format.md`](docs/07_card_grid_binary_format.md).** Still to do: Moon (after 3.7) and Earth (after 3.8–3.12). **New files for decision 007:** the Mars and Moon card grids at H3 res 5, one file per H3 base cell (e.g. `app/data/marte/<base_cell>.json`, `app/data/luna/<base_cell>.json`, ~600 KB each), in the same column format as `tierra.json`; update the data contract in `app/README.md` and `src/analogs/export.py`. Round values (or use a compact binary) to keep each file small.
- [ ] **3.17** Validate: known analogs (Atacama, Río Tinto, Devon, Antarctica…) must rank high for their matching sites.

## Phase 4 · Integration (`app/`)

- [ ] **4.1** Load `config.json`, `objetivos.json`, `tierra.json` and `analogos_conocidos.json` at startup.
- [ ] **4.2** Port the `similarity.py` formula to JavaScript and check that it gives 37.5 / 82.5 / 77.5 on the test example.
- [ ] **4.3** Filters: "What do you want to test?" (test → weights) and "Where?" (target site).
- [ ] **4.4** When a target is chosen: the camera flies there, Earth is colored by index (0–100) and Earth flies to the best match.
- [ ] **4.5** Match card: index, score per variable (target and Earth values, units and source), "not analog" block (gravity, pressure…) and test validity.
- [ ] **4.6** Browse the 2nd, 3rd… best matches.
- [ ] **4.7** Reverse direction: click on Earth → which Moon or Mars place it most resembles.
- [ ] **4.8** Show a clearly visible warning when the data is mock (`_aviso`).
- [ ] **4.9** **Main interaction (decision 007): click ANY point of the Moon or Mars** → find its H3 res 5 cell (lat/lon from 2.1 + `h3-js`) → download that region's file if not loaded yet → take its card → compute the index against every Earth cell in the browser → colour Earth, fly to the best match (2.4) and open the match card (4.5). Clicking a target site still uses that site's own footprint card. Needs 3.5, 3.7, 3.16 and 4.2.

## Phase 5 · Data layers on the globes (`app/`)

- [ ] **5.1** Export each variable as an equirectangular PNG from Python (`outputs/maps/`).
- [ ] **5.2** Add them to Cesium as transparent layers (`SingleTileImageryProvider`) with toggles.
- [ ] **5.3** H3 hexagon layer on Earth colored by index.
- [ ] **5.4** Legend and color scale for each layer.
- [ ] **5.5** Moon: Diviner layer (extreme cold, polar ice).
- [ ] **5.6** (Optional, if time allows) Pixel-level values for the variables that have them (e.g. slope at ~460 m): store them as "data tiles" (like map tiles) and read the exact pixel in the browser on click, on top of the ~9 km card.
## Phase 6 · Polish and presentation

- [ ] **6.1** Clean interface: title, short instructions and a guided tour ("try Jezero").
- [ ] **6.2** Performance: limit tiles, test on laptop and phone.
- [ ] **6.3** "Sources and method" section: PDS, Trek, GIBS, Copernicus, JAXA, CSA and the formula.
- [ ] **6.4** Demo video in case the connection fails.
- [ ] **6.5** Slides: problem → data → method → demo → limitations.
- [ ] **6.6** Review the final Space Apps submission (app link, repository, video).
