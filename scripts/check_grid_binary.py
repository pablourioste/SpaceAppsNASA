"""Check an exported card grid (any body): decode every region file and compare with the source.

    python scripts/check_grid_binary.py marte data/processed/mars_h3r5.parquet

For every column: no-data cells must match, and the max error must be <= scale/2 (values outside
the encodable range are clipped and reported separately). Exit code 1 if something is wrong.
"""
import gzip
import json
import sys
from pathlib import Path

import h3.api.basic_int as h3i
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analogs.paths import APP_DATA  # noqa: E402


def main(body: str, parquet: str) -> int:
    folder = APP_DATA / body
    idx = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    names = [c["name"] for c in idx["columns"]]
    df = pd.read_parquet(parquet, columns=["h3", *names]).set_index("h3")
    res0 = {h3i.get_base_cell_number(c): c for c in h3i.get_res0_cells()}
    worst = dict.fromkeys(names, 0.0)
    clipped = dict.fromkeys(names, 0)
    nan_mismatch = 0
    for r, meta in idx["regions"].items():
        raw = gzip.decompress((folder / meta["file"]).read_bytes())
        cells = sorted(h3i.cell_to_children(res0[int(r)], idx["h3_resolution"]))
        assert len(cells) == meta["n_cells"], f"region {r}: {len(cells)} cells, index says {meta['n_cells']}"
        ref_all = df.reindex([h3i.int_to_str(c) for c in cells])
        off = 0
        for col in idx["columns"]:
            size, nod = (1, 255) if col["dtype"] == "u1" else (2, 65535)
            q = np.frombuffer(raw, dtype=f"<u{size}", count=len(cells), offset=off)
            off += len(cells) * size
            v = np.where(q == nod, np.nan, q * col["scale"] + col["offset"])
            ref = ref_all[col["name"]].to_numpy(dtype=float)
            nan_mismatch += int((np.isnan(v) != np.isnan(ref)).sum())
            hi = col["offset"] + (nod - 1) * col["scale"]
            ok = np.isfinite(v) & np.isfinite(ref)
            inside = ok & (ref >= col["offset"]) & (ref <= hi)
            clipped[col["name"]] += int((ok & ~inside).sum())
            if inside.any():
                worst[col["name"]] = max(worst[col["name"]], float(np.abs(v[inside] - ref[inside]).max()))
        assert off == len(raw), f"region {r}: {len(raw) - off} unread bytes"
    bad = nan_mismatch > 0
    print(f"{body}: {len(idx['regions'])} regions, {idx['n_cells']:,} cells, no-data mismatches: {nan_mismatch}")
    for c in idx["columns"]:
        ok = worst[c["name"]] <= c["scale"] / 2 + 1e-6
        bad |= not ok
        print(f"  {c['name']:26s} max error {worst[c['name']]:.4g} (≤ {c['scale'] / 2:g}) "
              f"{'OK' if ok else 'TOO BIG'}  clipped: {clipped[c['name']]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
