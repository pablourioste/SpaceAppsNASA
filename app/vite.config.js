import { cpSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import cesium from 'vite-plugin-cesium';

// app/data/ (the index written by src/analogs/export.py) is served at /data/
// during development and copied as-is to dist/data/ on build.
const copyIndex = () => ({
  name: 'copy-app-data',
  closeBundle() {
    const src = resolve(__dirname, 'data');
    if (existsSync(src)) cpSync(src, resolve(__dirname, 'dist/data'), { recursive: true });
  },
});

export default defineConfig({
  base: './',
  plugins: [cesium(), copyIndex()],
});
