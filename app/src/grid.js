// Reads the planet-wide card grids written by src/analogs/export.py (write_grid_binary):
//
//   data/<body>/index.json     columns (dtype, scale, offset, unit, source) and regions
//   data/<body>/rNNN.bin.gz    one gzip file per H3 base cell NNN
//
// Inside a region (after gunzip): one block per column (order of index.json), each with one
// little-endian unsigned int per cell (uint8 "u1" or uint16 "u2").
//   value = stored * scale + offset;  stored = 255 / 65535 → no data (NaN).
// Cells are in ASCENDING H3 index order among the children of the base cell, so their ids are
// not stored: we rebuild the same list here with h3-js.
import { cellToChildren, getBaseCellNumber, getRes0Cells, latLngToCell } from 'h3-js';

const BASE = `${import.meta.env.BASE_URL}data/`;
const RES0 = new Map(getRes0Cells().map((c) => [getBaseCellNumber(c), c]));
const NODATA = { u1: 255, u2: 65535 };
const BYTES = { u1: 1, u2: 2 };

const isGzip = (u8) => u8[0] === 0x1f && u8[1] === 0x8b;

async function gunzip(buffer) {
  const u8 = new Uint8Array(buffer);
  // A server may already have decoded it (Content-Encoding: gzip): then it is raw bytes
  if (!isGzip(u8)) return buffer;
  const stream = new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}

const byH3 = (a, b) => (BigInt(`0x${a}`) < BigInt(`0x${b}`) ? -1 : 1);

export class CardGrid {
  /** @param {string} body folder under app/data/ (e.g. "marte") */
  constructor(body) {
    this.body = body;
    this.index = null;
    this.regions = new Map(); // base cell → Promise<{cells, rowOf, columns}>
  }

  async load() {
    if (!this.index) {
      const res = await fetch(`${BASE}${this.body}/index.json`);
      if (!res.ok) throw new Error(`No grid for ${this.body} (HTTP ${res.status})`);
      this.index = await res.json();
    }
    return this.index;
  }

  /** Download and decode one region (cached). */
  region(base) {
    if (!this.regions.has(base)) {
      this.regions.set(base, (async () => {
        const index = await this.load();
        const meta = index.regions[String(base)];
        if (!meta) return null;
        const res = await fetch(`${BASE}${this.body}/${meta.file}`);
        const raw = await gunzip(await res.arrayBuffer());
        const cells = cellToChildren(RES0.get(base), index.h3_resolution).sort(byH3);
        if (cells.length !== meta.n_cells) throw new Error(`Region ${base}: cell count mismatch`);
        const columns = {};
        let offset = 0;
        for (const col of index.columns) {
          const n = cells.length;
          const arr = col.dtype === 'u1'
            ? new Uint8Array(raw, offset, n)
            : new Uint16Array(raw.slice(offset, offset + 2 * n)); // copy: keeps 2-byte alignment
          columns[col.name] = { ...col, arr };
          offset += n * BYTES[col.dtype];
        }
        return { cells, rowOf: new Map(cells.map((c, i) => [c, i])), columns };
      })());
    }
    return this.regions.get(base);
  }

  /** Card of the cell that contains lat/lon (degrees): { h3, values: {name: number|NaN}, columns } */
  async cardAt(lat, lon) {
    const index = await this.load();
    const h3 = latLngToCell(lat, lon, index.h3_resolution);
    const reg = await this.region(getBaseCellNumber(h3));
    if (!reg) return null;
    const row = reg.rowOf.get(h3);
    const values = {};
    for (const [name, col] of Object.entries(reg.columns)) {
      const q = col.arr[row];
      values[name] = q === NODATA[col.dtype] ? NaN : q * col.scale + col.offset;
    }
    return { h3, values, columns: index.columns };
  }
}
