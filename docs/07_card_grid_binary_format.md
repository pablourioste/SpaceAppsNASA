# 07 · Card grids for the web: compact binary format

How a planet-wide card grid (one row per H3 cell) is shipped to the web app, and **how to do the
same for Earth and the Moon**. Implemented for Mars (ROADMAP 3.16): 2,016,842 cells, 14 variables,
**11 MB** in 122 files of 68–106 KB. The app downloads only the region that was clicked.

Code: [`src/analogs/export.py`](../src/analogs/export.py) (`write_grid_binary`) ·
reader: [`app/src/grid.js`](../app/src/grid.js) (`CardGrid`) ·
check: [`scripts/check_grid_binary.py`](../scripts/check_grid_binary.py).

## 1. The idea

| Step | What | Why |
|---|---|---|
| Quantize | each value → small unsigned integer: `stored = round((value − offset) / scale)` | 1 or 2 bytes instead of ~6 characters of JSON |
| No data | the largest integer of the type (`255` for `u1`, `65535` for `u2`) | no separate mask needed |
| Split by region | one file per **H3 base cell** (122 regions) | the app loads ~100 KB per click, not the whole planet |
| No cell ids | cells are stored in **ascending H3 index** among the children of the base cell | the app rebuilds the same list with `h3-js`, so ids cost 0 bytes |
| Column blocks | inside a file: all values of column 1, then column 2… | similar numbers next to each other compress much better |
| gzip | each file is gzip-compressed (level 9) | ~3× smaller; the browser decompresses it natively (`DecompressionStream`) |

Decoding: `value = stored × scale + offset`, or `NaN` if `stored` is the no-data value.
Maximum rounding error = `scale / 2`.

## 2. Files

```
app/data/<body>/index.json      what is inside (below)
app/data/<body>/r000.bin.gz     region = H3 base cell 0
…
app/data/<body>/r121.bin.gz     region = H3 base cell 121
```

`index.json`:

```json
{
  "_aviso": "",                      // non-empty = mock data, the app must show it
  "body": "marte",
  "h3_resolution": 5,
  "generated": "2026-11-14",
  "n_cells": 2016842,
  "columns": [
    {"name": "slope_deg", "dtype": "u1", "scale": 0.25, "offset": 0, "unit": "°",
     "label": "Slope (median, ~460 m baseline)", "source": "MGS MOLA MEGDR …"},
    …
  ],
  "regions": {"0": {"file": "r000.bin.gz", "n_cells": 16807, "bytes": 81234}, …}
}
```

Region file, after gunzip (`n` = `n_cells` of the region):

```
[ column 1: n × u1 or u2 ][ column 2: n × … ] … [ last column ]     little-endian, no header
```

Cell `i` of the region = the `i`-th element of
`sorted(cell_to_children(<res-0 cell of this base cell>, h3_resolution))` (ascending H3 index).
Pentagon base cells have fewer children (e.g. 16,807 vs 16,807 − …): always use `n_cells`.

## 3. How to do it for another body (Earth, Moon)

1. **Build the card grid** as a table with one row per H3 cell and a column `h3` (string id),
   like `data/processed/mars_h3r5.parquet` (Mars: `scripts/build_mars_grid.py`).
   **Include every cell of every region** (NaN where there is no data). The format assumes all
   children of each base cell are present. For Earth, ocean cells are simply NaN: runs of
   no-data compress to almost nothing.
2. **Choose the columns** and their encoding, a dict like `MARS_WEB_COLUMNS` in `export.py`:

   ```python
   EARTH_WEB_COLUMNS = {
       # name: (dtype, scale, offset, unit, label)
       "slope_deg":  ("u1", 0.25, 0.0,   "°", "Slope (median, ~460 m baseline)"),
       "t_mean_K":   ("u1", 1.0,  150.0, "K", "Mean surface temperature"),
       ...
   }
   EARTH_SOURCES = {"slope_deg": "Copernicus DEM GLO-30 (resampled to ~460 m)", ...}
   ```

   **Use the same name, unit and (ideally) the same scale as Mars for every shared variable**:
   the app compares them directly.
3. **Pick `dtype`, `scale`, `offset`** so the whole range fits and the error is small enough:
   - range that fits = `offset … offset + (max − 1) × scale` with `max` = 255 (`u1`) or 65535 (`u2`);
   - error = `scale / 2`; keep it well below the variable's **tolerance** in `configs/variables.yaml`
     (e.g. slope tolerance 5° vs error 0.125°);
   - prefer `u1` (1 byte); use `u2` only when needed (elevation, thermal inertia).
   Values outside the range are **clipped** (and counted by the check), never lost as no-data.
4. **Write it**:

   ```python
   from analogs.export import write_grid_binary
   write_grid_binary(df, "tierra", EARTH_WEB_COLUMNS, EARTH_SOURCES)   # → app/data/tierra/
   write_grid_binary(df, "luna",   MOON_WEB_COLUMNS,  MOON_SOURCES)    # → app/data/luna/
   ```

5. **Check it** (decodes every file and compares with the table):

   ```bash
   python scripts/check_grid_binary.py tierra data/processed/earth_h3r4.parquet
   ```

   Must print `no-data mismatches: 0` and `OK` for every column.
6. **Read it in the app**: `new CardGrid('tierra')`, then `await grid.cardAt(lat, lon)` →
   `{h3, values: {slope_deg: …, …}}` (works for any body and any H3 resolution).

## 4. Mars encoding (reference)

| Column | dtype | scale | offset | Range | Max error |
|---|---|---|---|---|---|
| `slope_deg`, `roughness_deg` | u1 | 0.25 | 0 | 0–63.5° | 0.125° |
| `t_mean_K`, `t_max_K`, `t_night_K` | u1 | 1 | 100 | 100–354 K | 0.5 K |
| `dust_aod` | u1 | 0.01 | 0 | 0–2.54 | 0.005 (47 cells clipped) |
| `ice_depth_m` | u1 | 0.5 | 0 | 0–127 m | exact (classes 0.5 / 3 / 5 / 10) |
| `sun_elev_max_deg` | u1 | 0.5 | 0 | 0–127° | 0.25° |
| `mola_measured_frac` | u1 | 0.005 | 0 | 0–1.27 | 0.0025 |
| `grs_h2o_wt_pct` | u1 | 0.05 | 0 | 0–12.7 wt% | 0.025 |
| `grs_cl_wt_pct` | u1 | 0.01 | 0 | 0–2.54 wt% | 0.005 |
| `p_surf_Pa` | u1 | 5 | 0 | 0–1270 Pa | 2.5 Pa |
| `elevation_m` | u2 | 1 | −10000 | −10000–55534 m | 0.5 m |
| `thermal_inertia_day_SI` | u2 | 1 | 0 | 0–65534 | 0.5 |

Checked 2026-11-14: Python round trip (`check_grid_binary.py`) and browser (`CardGrid`) give the
same cells, the same order and values within `scale/2` (Jezero, Gale, Hellas, north pole).

## 5. Target sites

The real cards of each body's target sites go next to its grid, as readable JSON:
`app/data/<body>/objetivos.json` (`write_mars_targets` for Mars), same shape as
`app/data/objetivos.json` plus `extras` (the other card columns) and `h3` (their cell).

They are **not** written into `app/data/objetivos.json` on purpose: that file belongs to the mock
package (`config.json` + `objetivos.json` + `tierra.json`), and `scripts/build_comparator_data.py`
rejects packages that mix real and mock files. When the Moon and Earth are real, the package can be
regenerated as a whole.
