// Screen ↔ latitude/longitude helpers for any body.
//
// Latitude convention (see data/README.md):
//   - Mars and Moon: PLANETOCENTRIC latitude, the one used by PDS products (MOLA, TES, GRS…).
//   - Earth: GEODETIC latitude (WGS84), the one used by Earth datasets (MODIS, Copernicus…).
// Longitude: −180…180, positive east, for all bodies.
import * as Cesium from 'cesium';

const { toDegrees, toRadians } = Cesium.Math;

/** Screen position → { lat, lon } in degrees, or null if the click misses the globe. */
export function pickLatLon(viewer, ellipsoid, latitudeType, screenPosition) {
  const cartesian = viewer.camera.pickEllipsoid(screenPosition, ellipsoid);
  if (!cartesian) return null;
  return cartesianToLatLon(cartesian, ellipsoid, latitudeType);
}

export function cartesianToLatLon(cartesian, ellipsoid, latitudeType) {
  const lon = toDegrees(Math.atan2(cartesian.y, cartesian.x));
  const lat =
    latitudeType === 'planetocentric'
      ? toDegrees(Math.atan2(cartesian.z, Math.hypot(cartesian.x, cartesian.y)))
      : toDegrees(Cesium.Cartographic.fromCartesian(cartesian, ellipsoid).latitude);
  return { lat, lon };
}

/** { lat, lon } in degrees → point on the ellipsoid surface (optionally raised by height metres). */
export function latLonToCartesian(lat, lon, ellipsoid, latitudeType, height = 0) {
  if (latitudeType !== 'planetocentric') {
    return Cesium.Cartesian3.fromDegrees(lon, lat, height, ellipsoid);
  }
  // Planetocentric: walk along the ray from the centre until it meets the ellipsoid
  const φ = toRadians(lat);
  const λ = toRadians(lon);
  const dir = new Cesium.Cartesian3(Math.cos(φ) * Math.cos(λ), Math.cos(φ) * Math.sin(λ), Math.sin(φ));
  const { x: a, y: b, z: c } = ellipsoid.radii;
  const r = 1 / Math.sqrt((dir.x / a) ** 2 + (dir.y / b) ** 2 + (dir.z / c) ** 2);
  const surface = Cesium.Cartesian3.multiplyByScalar(dir, r, new Cesium.Cartesian3());
  if (!height) return surface;
  const up = ellipsoid.geodeticSurfaceNormal(surface, new Cesium.Cartesian3());
  return Cesium.Cartesian3.add(surface, Cesium.Cartesian3.multiplyByScalar(up, height, up), surface);
}

/** 18.4, 77.5 → "18.400° N, 77.500° E" */
export function formatLatLon({ lat, lon }, digits = 3) {
  const ns = lat >= 0 ? 'N' : 'S';
  const ew = lon >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(digits)}° ${ns}, ${Math.abs(lon).toFixed(digits)}° ${ew}`;
}
