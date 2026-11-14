# Roadmap: phases and tasks

> Project tracking list. Tick each task when it is done: `- [ ]` → `- [x]`.
> Last update: 2026-11-14.

**Legend:** `app/` = the web app (Vite + CesiumJS) · `src/analogs/` = the engine and Python preprocessing · `app/data/` = the index the app reads (format in [`app/README.md`](app/README.md)).

**Progress:** 27 / 60 tasks done.

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
- [ ] **3.5** Extract the variables at each Mars target site: slope, roughness, thermal inertia, hydrogen, temperature and dust. *Draft code in `src/analogs/mars.py` + `scripts/build_mars_features.py` (readers checked on MOLA, TES TI and GRS; not run end-to-end yet).*
  **Slope and roughness at ~463 m (decided):** use MOLA MEGDR 128 px/deg instead of the 16 px/deg global map (3.7 km). The ~10 km site footprint then holds ~20×20 pixels instead of 3×3, and the baseline matches the Moon (LOLA `ldem_64`, ~474 m) and Earth (Copernicus DEM resampled to ~460 m), as decision 006 requires. Tiles in `data/raw/mars/mola_megdr_128ppd/` (`python scripts/download_data.py mola128`, only the tiles that contain a target site).
  > ⚠️ **Warning: interpolated cells.** MOLA measures along the spacecraft ground tracks; near the equator the gaps between tracks can be several km wide, so at 128 px/deg many cells have **no laser shot and are interpolated**. In those cells the slope comes out **smoother than reality**. For every site, use the shots-per-cell tile (`megc…hb`) to report the **fraction of measured cells** in the footprint, store it as a QC column (e.g. `mola_measured_frac`) and flag sites where it is low (threshold to decide).
  > **Measured so far (2026-11-14):** at the 12 Mars sites only **15–46 %** of the 128 px/deg cells in the footprint have a laser shot (Viking 1 15 %, Arcadia 19 %, Jezero 46 %). So a fixed "< 50 %" threshold would flag every site: report the fraction on the card instead of discarding sites, and consider computing slope only from measured cells.
  **To decide when doing 3.5:**
  - Source for `t_mean_K`: the TES retrievals are daytime only, so a night/diurnal-mean surface temperature needs another product (e.g. MCS surface temperature, PDS Atmospheres).
  - GRS element maps have no data north of ~45° (Arcadia, Phoenix, Viking 2): use the NS epithermal neutron flux there for ice/hydrogen.
  - Whether to add the Mars-only extras (thermal inertia, GRS H₂O/Cl, surface pressure) to `configs/variables.yaml`.

### 3B · Moon
- [ ] **3.6** Download Diviner PRP (temperature, ice depth) and LOLA.
- [ ] **3.7** Extract the variables at each Moon target site.

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
- [ ] **3.17** Validate: known analogs (Atacama, Río Tinto, Devon, Antarctica…) must rank high for their matching sites.

## Phase 4 · Integration (`app/`)

- [ ] **4.1** Load `config.json`, `objetivos.json`, `tierra.json` and `analogos_conocidos.json` at startup.
- [ ] **4.2** Port the `similarity.py` formula to JavaScript and check that it gives 37.5 / 82.5 / 77.5 on the test example.
- [ ] **4.3** Filters: "What do you want to test?" (test → weights) and "Where?" (target site).
- [ ] **4.4** When a target is chosen: the camera flies there, Earth is colored by index (0–100) and Earth flies to the best match.
- [ ] **4.5** Match card: index, score per variable (target and Earth values, units and source), "not analog" block (gravity, pressure…) and test validity.
- [ ] **4.6** Browse the 2nd, 3rd… best matches.
- [ ] **4.7** Reverse direction: click on Earth → which Moon or Mars site it most resembles.
  *Clicking any point of Mars (not only the target sites) needs Mars-wide slope: download the 10 remaining MOLA 128 px/deg tiles first (~2 GB more; see 5.6).*
- [ ] **4.8** Show a clearly visible warning when the data is mock (`_aviso`).

## Phase 5 · Data layers on the globes (`app/`)

- [ ] **5.1** Export each variable as an equirectangular PNG from Python (`outputs/maps/`).
- [ ] **5.2** Add them to Cesium as transparent layers (`SingleTileImageryProvider`) with toggles.
- [ ] **5.3** H3 hexagon layer on Earth colored by index.
- [ ] **5.4** Legend and color scale for each layer.
- [ ] **5.5** Moon: Diviner layer (extreme cold, polar ice).
- [ ] **5.6** (Later) Mars-wide slope/roughness at ~463 m: download the 10 MOLA 128 px/deg tiles not yet downloaded (16 in total, ~3.1 GB with the shots-per-cell tiles) — better outside OneDrive with `ANALOGS_DATA_DIR`. Needed for the global slope layer and for 4.7 on any point of Mars. Poles (|lat| > 88°) need the MOLA polar products.

## Phase 6 · Polish and presentation

- [ ] **6.1** Clean interface: title, short instructions and a guided tour ("try Jezero").
- [ ] **6.2** Performance: limit tiles, test on laptop and phone.
- [ ] **6.3** "Sources and method" section: PDS, Trek, GIBS, Copernicus, JAXA, CSA and the formula.
- [ ] **6.4** Demo video in case the connection fails.
- [ ] **6.5** Slides: problem → data → method → demo → limitations.
- [ ] **6.6** Review the final Space Apps submission (app link, repository, video).
