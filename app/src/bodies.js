// Per-body configuration: ellipsoid, imagery layers and initial view.
// All layers are public and need no account (checked on 2026-11-14).
//
// Each body has up to three layers:
//   base   – global imagery, always on
//   detail – high-resolution imagery drawn on top once the camera is close enough
//   relief – shaded relief, toggled from the toolbar
import * as Cesium from 'cesium';

const TREK = 'https://trek.nasa.gov/tiles';
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';

// Trek tiles: equirectangular, level 0 = 2×1 tiles of 256 px.
// maximumLevel = deepest level Trek actually serves (checked); beyond it Cesium upsamples.
const trekLayer = (body, layer, ellipsoid, maximumLevel, credit, ext = 'jpg') => ({
  make: () =>
    new Cesium.UrlTemplateImageryProvider({
      url: `${TREK}/${body}/EQ/${layer}/1.0.0/default/default028mm/{z}/{y}/{x}.${ext}`,
      tilingScheme: new Cesium.GeographicTilingScheme({ ellipsoid }),
      maximumLevel,
      credit,
    }),
});

// GIBS tiles in Web Mercator (EPSG:3857), 256 px, power-of-two pyramid
const gibsLayer = (layer, matrixLevel, credit) => ({
  make: () =>
    new Cesium.UrlTemplateImageryProvider({
      url: `${GIBS}/${layer}/default/GoogleMapsCompatible_Level${matrixLevel}/{z}/{y}/{x}.jpeg`,
      tilingScheme: new Cesium.WebMercatorTilingScheme(),
      maximumLevel: matrixLevel,
      credit,
    }),
});

export const BODIES = {
  earth: {
    name: 'Earth',
    ellipsoid: Cesium.Ellipsoid.WGS84,
    latitudeType: 'geodetic', // Earth datasets (MODIS, Copernicus…) use WGS84 geodetic latitude
    atmosphere: true,
    home: { lon: 0, lat: 20, height: 2.0e7 },
    flyHeight: 8.0e5, // default camera height (m) when flying to a site
    base: gibsLayer('BlueMarble_ShadedRelief_Bathymetry', 8, 'NASA GIBS · Blue Marble'),
    // Sentinel-2 cloudless 2016 (EOX, CC BY 4.0), ~10 m/px, Web Mercator
    detail: {
      fromLevel: 5,
      make: () =>
        new Cesium.UrlTemplateImageryProvider({
          url: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg',
          tilingScheme: new Cesium.WebMercatorTilingScheme(),
          maximumLevel: 14,
          credit: 'Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016)',
        }),
    },
    relief: gibsLayer('ASTER_GDEM_Color_Shaded_Relief', 12, 'NASA GIBS · ASTER GDEM'),
  },
  mars: {
    name: 'Mars',
    ellipsoid: Cesium.Ellipsoid.MARS,
    latitudeType: 'planetocentric', // PDS products (MOLA, TES, GRS) use planetocentric latitude
    atmosphere: false,
    home: { lon: 0, lat: 10, height: 1.1e7 },
    flyHeight: 6.0e5,
    base: trekLayer('Mars', 'Mars_Viking_MDIM21_ClrMosaic_global_232m', Cesium.Ellipsoid.MARS, 7,
      'NASA Mars Trek · Viking MDIM 2.1'),
    // MRO CTX global mosaic, ~5 m/px, greyscale (listed by Mars Trek, served by Esri)
    detail: {
      fromLevel: 6,
      make: () =>
        new Cesium.UrlTemplateImageryProvider({
          url: 'https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX/MapServer/tile/{z}/{y}/{x}',
          tilingScheme: new Cesium.GeographicTilingScheme({ ellipsoid: Cesium.Ellipsoid.MARS }),
          tileWidth: 512,
          tileHeight: 512,
          maximumLevel: 12,
          credit: 'MRO CTX global mosaic · NASA/JPL/MSSS/Caltech Murray Lab/Esri',
        }),
    },
    relief: trekLayer('Mars', 'Mars_MGS_MOLA_ClrShade_merge_global_463m', Cesium.Ellipsoid.MARS, 7,
      'NASA Mars Trek · MGS MOLA'),
  },
  moon: {
    name: 'Moon',
    ellipsoid: Cesium.Ellipsoid.MOON,
    latitudeType: 'planetocentric',
    atmosphere: false,
    home: { lon: 0, lat: 0, height: 6.0e6 },
    flyHeight: 4.0e5,
    base: trekLayer('Moon', 'LRO_WAC_Mosaic_Global_303ppd_v02', Cesium.Ellipsoid.MOON, 8,
      'NASA Moon Trek · LRO WAC'),
    detail: null,
    // LOLA colour hillshade v6 (Moon Trek serves it as PNG, not JPG)
    relief: trekLayer('Moon', 'LRO_LOLA_ClrShade_Global_256ppd_v06', Cesium.Ellipsoid.MOON, 8,
      'NASA Moon Trek · LRO LOLA', 'png'),
  },
};
