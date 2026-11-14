"""PASO 4: escribir el ÍNDICE que lee la app (app/data/).

La app no descarga datos de NASA: solo lee estos ficheros, que pesan pocos MB.
El formato está explicado en app/README.md. Lo usan tanto el flujo real
(scripts/run_pipeline.py) como los datos falsos (scripts/make_mock_data.py).

    app/data/config.json              variables, pruebas y el bloque "no análogo" de cada cuerpo
    app/data/objetivos.json           un objeto por sitio objetivo (Luna/Marte) con su ficha
    app/data/tierra.json              la ficha de cada hexágono de la Tierra, por columnas
    app/data/analogos_conocidos.json  análogos ya estudiados (para marcarlos y validar)
"""
import json

import numpy as np
import pandas as pd

from .paths import APP_DATA


def _clean(value, ndigits=3):
    """NaN → null y floats redondeados, para un JSON válido y ligero."""
    if isinstance(value, (float, np.floating)):
        return None if np.isnan(value) else round(float(value), ndigits)
    if isinstance(value, np.integer):
        return int(value)
    return value


def _write(name: str, payload) -> None:
    APP_DATA.mkdir(parents=True, exist_ok=True)
    with open(APP_DATA / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))


def write_index(targets: pd.DataFrame, earth: pd.DataFrame, variables_cfg: dict, pruebas: dict,
                known_analogs: pd.DataFrame | None = None, mock: bool = False) -> None:
    """Escribe los cuatro ficheros de app/data/.

    targets: una fila por objetivo; columnas id, name, body, lat, lon, type + variables
    earth:   una fila por hexágono; columnas cell_id, lat, lon + variables (+ operabilidad)
    """
    aviso = {"_aviso": "DATOS FALSOS generados por scripts/make_mock_data.py"} if mock else {}
    var_names = [v for v in variables_cfg["variables"] if v in earth.columns or v in targets.columns]

    _write("config.json", {**aviso,
                           "variables": variables_cfg["variables"],
                           "operability": variables_cfg.get("operability", {}),
                           "bodies": variables_cfg["bodies"],
                           "pruebas": pruebas})

    meta = ["id", "name", "body", "lat", "lon", "type"]
    objetivos = [{**{k: _clean(r[k]) for k in meta if k in r},
                  "features": {v: _clean(r[v]) for v in var_names if v in r}}
                 for r in targets.to_dict("records")]
    _write("objetivos.json", {**aviso, "objetivos": objetivos})

    _write("tierra.json", {**aviso,
                           "n_cells": len(earth),
                           "columns": {c: [_clean(x) for x in earth[c].tolist()] for c in earth.columns}})

    if known_analogs is not None:
        _write("analogos_conocidos.json",
               {"analogos": [{k: _clean(v) for k, v in r.items()} for r in known_analogs.to_dict("records")]})


# ======================================================================================
# Planet-wide card grids (decision 007, ROADMAP 3.16): compact binary, one file per region
# ======================================================================================
#
#   app/data/<body>/index.json      columns (dtype, scale, offset, unit, source), regions, order
#   app/data/<body>/rNNN.bin.gz     one file per H3 base cell NNN (0–121), gzip-compressed
#
# Inside a region file (after gunzip): one block per column, in the order of index.json;
# each block holds one little-endian unsigned integer per cell (uint8 or uint16).
#   value = stored × scale + offset;  stored = max of the dtype (255 / 65535) → no data.
# Cells are ordered by ASCENDING H3 index among the res-5 children of the base cell, so the
# cell ids are not stored: the app rebuilds the same list with h3-js (cellToChildren + sort).

# name → (dtype, scale, offset, unit, label)
MARS_WEB_COLUMNS: dict[str, tuple[str, float, float, str, str]] = {
    "slope_deg":              ("u1", 0.25, 0.0, "°", "Slope (median, ~460 m baseline)"),
    "roughness_deg":          ("u1", 0.25, 0.0, "°", "Roughness (RMS slope after removing a plane)"),
    "t_mean_K":               ("u1", 1.0, 100.0, "K", "Mean surface temperature ((day + night) / 2)"),
    "t_max_K":                ("u1", 1.0, 100.0, "K", "Max surface temperature (P95 of afternoon values)"),
    "t_night_K":              ("u1", 1.0, 100.0, "K", "Night surface temperature (~03 h)"),
    "dust_aod":               ("u1", 0.01, 0.0, "", "Dust optical depth (visible, ×2.6 from 9.3 µm)"),
    "ice_depth_m":            ("u1", 0.5, 0.0, "m", "Depth to water ice (SWIM class; 10 = no ice found)"),
    "sun_elev_max_deg":       ("u1", 0.5, 0.0, "°", "Highest noon Sun elevation over a year"),
    "mola_measured_frac":     ("u1", 0.005, 0.0, "", "Fraction of MOLA cells with a laser shot (QC)"),
    "grs_h2o_wt_pct":         ("u1", 0.05, 0.0, "wt%", "Water-equivalent hydrogen (GRS, 5°)"),
    "grs_cl_wt_pct":          ("u1", 0.01, 0.0, "wt%", "Chlorine (GRS, 5°)"),
    "p_surf_Pa":              ("u1", 5.0, 0.0, "Pa", "Surface pressure (TES)"),
    "elevation_m":            ("u2", 1.0, -10000.0, "m", "Elevation above the areoid (MOLA)"),
    "thermal_inertia_day_SI": ("u2", 1.0, 0.0, "J m⁻² K⁻¹ s⁻½", "Thermal inertia, day (TES)"),
}

MARS_SOURCES = {
    "slope_deg": "MGS MOLA MEGDR 128 px/deg + polar maps (PDS Geosciences)",
    "roughness_deg": "MGS MOLA MEGDR 128 px/deg + polar maps (PDS Geosciences)",
    "elevation_m": "MGS MOLA MEGDR 128 px/deg (PDS Geosciences)",
    "mola_measured_frac": "MGS MOLA MEGDR shots per cell (PDS Geosciences)",
    "t_mean_K": "MGS TES IR retrievals MY26 (day) + MRO MCS DDR MY31 (night), PDS Atmospheres",
    "t_max_K": "MGS TES IR retrievals MY26, Montabone et al. (PDS Atmospheres)",
    "t_night_K": "MRO MCS Derived Data Records v6.2, MY31 (PDS Atmospheres)",
    "dust_aod": "MGS TES IR retrievals MY26, Montabone et al. (PDS Atmospheres)",
    "p_surf_Pa": "MGS TES IR retrievals MY26, Montabone et al. (PDS Atmospheres)",
    "ice_depth_m": "SWIM 2.0 ice consistency (NASA MEP / PSI), threshold 0.25",
    "grs_h2o_wt_pct": "Mars Odyssey GRS element maps 5°×5° (PDS Geosciences)",
    "grs_cl_wt_pct": "Mars Odyssey GRS element maps 5°×5° (PDS Geosciences)",
    "thermal_inertia_day_SI": "MGS TES thermal inertia, Putzig & Mellon 2007 (PDS Geosciences)",
    "sun_elev_max_deg": "computed from latitude and obliquity (25.19°)",
}


def _quantize(values: np.ndarray, dtype: str, scale: float, offset: float) -> np.ndarray:
    nodata = 255 if dtype == "u1" else 65535
    q = np.round((np.asarray(values, dtype=np.float64) - offset) / scale)
    q = np.clip(q, 0, nodata - 1)                     # out-of-range values are clipped, not lost
    q[~np.isfinite(np.asarray(values, dtype=np.float64))] = nodata
    return q.astype("<u1" if dtype == "u1" else "<u2")


def write_grid_binary(df: pd.DataFrame, body: str, columns: dict, sources: dict) -> dict:
    """Write app/data/<body>/ from a card grid (one row per H3 cell, column `h3`)."""
    import datetime as dt
    import gzip

    import h3.api.basic_int as h3i

    out = APP_DATA / body
    out.mkdir(parents=True, exist_ok=True)
    ids = np.array([h3i.str_to_int(h) for h in df["h3"]], dtype=np.uint64)
    res = h3i.get_resolution(int(ids[0]))
    base = np.array([h3i.get_base_cell_number(int(c)) for c in ids])
    order = np.lexsort((ids, base))                   # by region, then ascending H3 index
    ids, base = ids[order], base[order]
    data = {name: df[name].to_numpy()[order] for name in columns}

    regions = {}
    starts = np.r_[0, np.flatnonzero(np.diff(base)) + 1, len(base)]
    for a, b in zip(starts[:-1], starts[1:]):
        r = int(base[a])
        blob = b"".join(_quantize(data[name][a:b], *columns[name][:3]).tobytes() for name in columns)
        fname = f"r{r:03d}.bin.gz"
        with open(out / fname, "wb") as f:
            f.write(gzip.compress(blob, compresslevel=9, mtime=0))
        regions[str(r)] = {"file": fname, "n_cells": int(b - a), "bytes": (out / fname).stat().st_size}

    index = {
        "_aviso": "",
        "body": body,
        "h3_resolution": res,
        "generated": dt.date.today().isoformat(),
        "n_cells": int(len(ids)),
        "encoding": "gzip; column blocks in the order of `columns`; little-endian unsigned ints; "
                    "value = stored*scale + offset; stored = max of dtype means no data",
        "cell_order": f"ascending H3 index among the res-{res} children of each base cell (region)",
        "columns": [{"name": n, "dtype": d, "scale": s, "offset": o, "unit": u, "label": lab,
                     "source": sources.get(n, "")}
                    for n, (d, s, o, u, lab) in columns.items()],
        "regions": regions,
    }
    with open(out / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    return index


def write_mars_targets(targets: pd.DataFrame, variables_cfg: dict) -> None:
    """Real cards of the Mars target sites → app/data/marte/objetivos.json.

    Kept apart from app/data/objetivos.json on purpose: that file is part of the mock package
    (config + objetivos + tierra) and scripts/build_comparator_data.py rejects packages that mix
    real and mock files. Same shape as objetivos.json, plus `extras` (other card columns) and `h3`.
    """
    var_names = list(variables_cfg["variables"])
    extras = [c for c in MARS_WEB_COLUMNS if c not in var_names]
    meta = ["id", "name", "body", "lat", "lon", "type", "h3"]
    mars = [{**{k: _clean(r[k]) for k in meta if k in r},
             "features": {v: _clean(r.get(v, np.nan)) for v in var_names},
             "extras": {v: _clean(r.get(v, np.nan)) for v in extras}}
            for r in targets.to_dict("records")]
    _write("marte/objetivos.json", {"_aviso": "", "objetivos": mars})
