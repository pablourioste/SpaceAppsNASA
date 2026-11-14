"""Máscara de la Tierra: dónde SÍ buscamos análogos (desiertos, polos, campos de lava)
y dónde NO (mar, bosques, cultivos, ciudades, humedales).

    python scripts/download_earth.py mask      # antes: MCD12C1 + GPM IMERG mensual
    python scripts/build_earth_mask.py

Entrada (data/raw/earth/):
  mcd12c1/        MODIS MCD12C1 v061: % de cada clase IGBP en cada celda de 0,05° (~5,6 km)
  imerg_monthly/  GPM IMERG v07 mensual, 0,1°, 2019–2023 → lluvia media anual (mm/año)

Regla (umbrales [supuesto], los fija Ciencia):
  tierra       = 100 − %agua ≥ 50
  hielo polar  = %nieve/hielo permanente ≥ 50
  desierto     = %suelo desnudo ≥ 50                      (sin mirar la lluvia: lava, salares)
  árido abierto= %(desnudo + matorral abierto + pradera) ≥ 60  Y  lluvia < 350 mm/año
  SE QUEDA     = tierra Y (hielo polar O desierto O árido abierto)
  Todo lo demás (bosques, sabanas, cultivos, ciudades, humedales, praderas húmedas) se quita.

Salida:
  data/interim/earth_mask_005deg.npz         la máscara píxel a píxel (clase 0–3) y la lluvia
  data/processed/earth_mask_h3r5.parquet     una fila por hexágono H3 res 5 (~17 km) con tierra
  data/processed/earth_mask_h3r4.parquet     ídem res 4 (~45 km)
  outputs/maps/earth_mask.png                mapa para revisar, con los análogos conocidos encima
  outputs/validation/earth_mask_known_analogs.csv   ¿cae cada análogo conocido dentro?
"""
import sys
from pathlib import Path

import h3
import h5py
import numpy as np
import pandas as pd
from pyhdf.SD import SD, SDC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analogs.paths import CATALOGS, INTERIM, MAPS, PROCESSED, RAW, VALIDATION  # noqa: E402

# --- Umbrales [supuesto] ---
MIN_LAND = 50          # % de tierra en la celda de 0,05°
MIN_SNOW = 50          # % nieve/hielo permanente → hielo polar
MIN_BARREN = 50        # % suelo desnudo → desierto (sin condición de lluvia)
MIN_DRY_OPEN = 60      # % desnudo + matorral abierto + pradera …
MAX_PRECIP = 350       # … y lluvia media < 350 mm/año → árido abierto (con 250 se perdían SP Crater,
                       #     Meteor Crater y Pilbara, que están en 300–320 mm)
MIN_CELL_FRAC = 0.25   # un hexágono se queda si ≥ 25 % de su tierra (en área) está en la máscara
                       #     (con 50 % se perdían campos de lava pequeños: Teide, Mauna Kea, Craters of the Moon)

# Clases IGBP (MCD12C1, Land_Cover_Type_1_Percent: índice = clase)
WATER, OPEN_SHRUB, GRASS, SNOW, BARREN = 0, 7, 10, 15, 16
FOREST = [1, 2, 3, 4, 5]
CLASS_NAMES = {0: "fuera", 1: "hielo polar", 2: "desierto (suelo desnudo)", 3: "árido abierto (matorral/estepa)"}

N_LAT, N_LON, RES = 3600, 7200, 0.05
LAT = 90 - RES / 2 - RES * np.arange(N_LAT)        # centros, de norte a sur
LON = -180 + RES / 2 + RES * np.arange(N_LON)


def read_mcd12c1() -> np.ndarray:
    f = sorted((RAW / "earth" / "mcd12c1").glob("MCD12C1*.hdf"))[-1]
    print(f"MCD12C1: {f.name}")
    pct = SD(str(f), SDC.READ).select("Land_Cover_Type_1_Percent").get()  # (3600, 7200, 17) uint8
    assert pct.shape == (N_LAT, N_LON, 17), pct.shape
    return pct


def read_precip_mm_year() -> np.ndarray:
    files = sorted((RAW / "earth" / "imerg_monthly").glob("3B-MO*.HDF5"))
    if not files:
        print("IMERG: no hay ficheros → máscara SIN lluvia (versión provisional, ver classify)")
        return np.full((N_LAT, N_LON), np.nan)
    print(f"IMERG: {len(files)} meses ({files[0].name[22:30]} … {files[-1].name[22:30]})")
    acc = np.zeros((N_LAT // 2, N_LON // 2))
    n = np.zeros_like(acc)
    for f in files:
        with h5py.File(f, "r") as h:
            p = h["Grid/precipitation"][0].astype("f8")          # (lon 3600, lat 1800), mm/h, lat ascendente
        p = p.T[::-1]                                             # → (lat de norte a sur, lon)
        ok = np.isfinite(p) & (p >= 0)
        acc[ok] += p[ok]
        n[ok] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(n >= 0.8 * len(files), acc / n, np.nan)   # mm/h, media de todos los meses
    mm_year = rate * 24 * 365.25
    return np.repeat(np.repeat(mm_year, 2, axis=0), 2, axis=1)    # 0,1° → 0,05°


def classify(pct: np.ndarray, precip: np.ndarray) -> np.ndarray:
    land = (100 - pct[..., WATER].astype(int)) >= MIN_LAND
    snow = pct[..., SNOW] >= MIN_SNOW
    barren = pct[..., BARREN] >= MIN_BARREN
    if np.isfinite(precip).any():
        dry_open = (pct[..., BARREN].astype(int) + pct[..., OPEN_SHRUB] + pct[..., GRASS]) >= MIN_DRY_OPEN
        arid = np.nan_to_num(precip, nan=np.inf) < MAX_PRECIP
    else:  # sin lluvia: la pradera NO entra (no sabemos si es estepa seca o pasto húmedo)
        dry_open = (pct[..., BARREN].astype(int) + pct[..., OPEN_SHRUB]) >= MIN_DRY_OPEN
        arid = np.ones_like(dry_open)
    cls = np.zeros((N_LAT, N_LON), np.uint8)
    cls[land & dry_open & arid] = 3
    cls[land & barren] = 2
    cls[land & snow] = 1
    return cls, land


def to_h3(cls: np.ndarray, land: np.ndarray, precip: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    i, j = np.nonzero(land)
    lat, lon = LAT[i], LON[j]
    w = np.cos(np.radians(lat))                                   # área del píxel ∝ cos(lat)
    print(f"Calculando H3 res 5 para {len(i):,} píxeles de tierra…")
    cells = [h3.latlng_to_cell(a, b, 5) for a, b in zip(lat, lon)]
    c = cls[i, j]
    df = pd.DataFrame({"cell": cells, "w": w, "kept_w": w * (c > 0), "precip_w": w * np.nan_to_num(precip[i, j]),
                       "precip_ok_w": w * np.isfinite(precip[i, j])})
    for k in (1, 2, 3):
        df[f"c{k}"] = w * (c == k)

    def aggregate(d: pd.DataFrame) -> pd.DataFrame:
        g = d.groupby("cell").sum(numeric_only=True)
        out = pd.DataFrame(index=g.index)
        out["kept_frac"] = g.kept_w / g.w
        out["precip_mm_year"] = (g.precip_w / g.precip_ok_w).where(g.precip_ok_w > 0)
        out["env"] = g[["c1", "c2", "c3"]].to_numpy().argmax(1) + 1
        out.loc[out.kept_frac == 0, "env"] = 0
        out["env_name"] = out.env.map(CLASS_NAMES)
        out["in_mask"] = out.kept_frac >= MIN_CELL_FRAC
        latlon = np.array([h3.cell_to_latlng(x) for x in out.index])
        out["lat"], out["lon"] = latlon[:, 0], latlon[:, 1]
        return out.reset_index()

    r5 = aggregate(df)
    df["cell"] = [h3.cell_to_parent(x, 4) for x in df.cell]       # mismo cálculo, un nivel arriba
    r4 = aggregate(df)
    return r5, r4


def validate(cls, pct, precip, r5, r4) -> pd.DataFrame:
    kn = pd.read_csv(CATALOGS / "known_analogs.csv")
    in5 = set(r5.cell[r5.in_mask])
    in4 = set(r4.cell[r4.in_mask])
    rows = []
    for _, a in kn.iterrows():
        i = int(np.clip((90 - a.lat) // RES, 0, N_LAT - 1))
        j = int(np.clip((a.lon + 180) // RES, 0, N_LON - 1))
        win = cls[max(i - 2, 0):i + 3, max(j - 2, 0):j + 3]        # ±2 píxeles ≈ ±11 km
        p = pct[i, j]
        rows.append(dict(
            name=a["name"], lat=a.lat, lon=a.lon,
            clase_pixel=CLASS_NAMES[int(cls[i, j])],
            dentro_pixel=bool(cls[i, j] > 0),
            dentro_11km=bool((win > 0).any()),
            dentro_h3r5=h3.latlng_to_cell(a.lat, a.lon, 5) in in5,
            dentro_h3r4=h3.latlng_to_cell(a.lat, a.lon, 4) in in4,
            pct_agua=int(p[WATER]), pct_desnudo=int(p[BARREN]), pct_matorral_abierto=int(p[OPEN_SHRUB]),
            pct_pradera=int(p[GRASS]), pct_nieve_hielo=int(p[SNOW]), pct_bosque=int(p[FOREST].sum()),
            lluvia_mm_ano=None if not np.isfinite(precip[i, j]) else round(float(precip[i, j])),
        ))
    return pd.DataFrame(rows)


def plot(cls, val: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    colors = ["#dfe6ee", "#5aa9e6", "#e0a458", "#b5c97a"]
    fig, ax = plt.subplots(figsize=(16, 8.4), dpi=110)
    ax.imshow(cls[::3, ::3], cmap=ListedColormap(colors), vmin=0, vmax=3, extent=(-180, 180, -90, 90),
              interpolation="nearest")
    ok = val.dentro_h3r5
    ax.scatter(val.lon[ok], val.lat[ok], s=36, c="#1b7f3b", edgecolors="white", linewidths=0.8, zorder=3)
    ax.scatter(val.lon[~ok], val.lat[~ok], s=46, marker="X", c="#c0262d", edgecolors="white", linewidths=0.8, zorder=3)
    for _, r in val.iterrows():
        ax.annotate(r["name"].split(" (")[0], (r.lon, r.lat), xytext=(4, 3), textcoords="offset points", fontsize=6.5)
    ax.legend(handles=[Patch(color=colors[k], label=CLASS_NAMES[k]) for k in (1, 2, 3)]
              + [Patch(color="#1b7f3b", label="análogo conocido dentro (H3 res 5)"),
                 Patch(color="#c0262d", label="análogo conocido FUERA")],
              loc="lower left", fontsize=8, framealpha=0.9)
    ax.set_title("Máscara de la Tierra: zonas donde buscamos análogos (MODIS MCD12C1 2025"
                 + (" + GPM IMERG 2019–2023)" if val.lluvia_mm_ano.notna().any() else ", SIN lluvia: provisional)"),
                 fontsize=11)
    ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    ax.set_xlabel("longitud (°E)"); ax.set_ylabel("latitud (°N)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    pct = read_mcd12c1()
    precip = read_precip_mm_year()
    cls, land = classify(pct, precip)

    w = np.cos(np.radians(LAT))[:, None]
    land_area = (w * land).sum()
    print("\n% de la tierra emergida (en área) en cada clase:")
    for k in (1, 2, 3):
        print(f"  {CLASS_NAMES[k]:34s} {100 * (w * (cls == k)).sum() / land_area:5.1f} %")
    print(f"  {'TOTAL dentro de la máscara':34s} {100 * (w * (cls > 0)).sum() / land_area:5.1f} %")

    INTERIM.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(INTERIM / "earth_mask_005deg.npz", cls=cls, land=land, precip_mm_year=precip.astype("f4"),
                        lat=LAT, lon=LON)

    r5, r4 = to_h3(cls, land, precip)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    r5.to_parquet(PROCESSED / "earth_mask_h3r5.parquet", index=False)
    r4.to_parquet(PROCESSED / "earth_mask_h3r4.parquet", index=False)
    for name, r in (("res 5 (~17 km)", r5), ("res 4 (~45 km)", r4)):
        print(f"H3 {name}: {len(r):,} hexágonos con tierra → {int(r.in_mask.sum()):,} dentro de la máscara")
        print("   " + ", ".join(f"{k}: {v:,}" for k, v in r[r.in_mask].env_name.value_counts().items()))

    val = validate(cls, pct, precip, r5, r4)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    val.to_csv(VALIDATION / "earth_mask_known_analogs.csv", index=False)
    print(f"\nAnálogos conocidos dentro: píxel {val.dentro_pixel.sum()}/{len(val)} · "
          f"±11 km {val.dentro_11km.sum()}/{len(val)} · H3 r5 {val.dentro_h3r5.sum()}/{len(val)} · "
          f"H3 r4 {val.dentro_h3r4.sum()}/{len(val)}")
    print(val[["name", "clase_pixel", "dentro_11km", "dentro_h3r5", "pct_desnudo", "pct_matorral_abierto",
               "pct_pradera", "pct_nieve_hielo", "pct_bosque", "lluvia_mm_ano"]].to_string(index=False))

    MAPS.mkdir(parents=True, exist_ok=True)
    plot(cls, val, MAPS / "earth_mask.png")
    print(f"\nMapa: {MAPS / 'earth_mask.png'}")


if __name__ == "__main__":
    main()
