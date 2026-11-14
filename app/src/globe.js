// Creates a Cesium globe for one body (earth, mars, moon).
import * as Cesium from 'cesium';
import { BODIES } from './bodies.js';
import { formatLatLon, latLonToCartesian, pickLatLon } from './coords.js';

const css = (c) => Cesium.Color.fromCssColorString(c);
const COLORS = {
  marker: css('#e2673a'),
  selected: css('#e2673a'),
  target: css('#f2c14e'), // target sites on the Moon / Mars
  analog: css('#4cc38a'), // known analogs on Earth
};
const LABEL_BG = css('rgba(16,20,31,0.85)');
const SITE_SIZE = 8;
const SELECTED_SIZE = 13;
// Points sit slightly above the surface so the globe never clips them, while still being
// depth-tested so sites on the far side of the planet stay hidden.
const SURFACE_OFFSET = 1000; // m

export function createGlobe(container, bodyKey) {
  const body = BODIES[bodyKey];
  const { ellipsoid } = body;

  const viewer = new Cesium.Viewer(container, {
    ellipsoid,
    baseLayer: new Cesium.ImageryLayer(body.base.make()),
    baseLayerPicker: false,
    geocoder: false,
    timeline: false,
    animation: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    skyAtmosphere: body.atmosphere ? undefined : false,
    // Cesium only adds stars by default with the Earth ellipsoid
    skyBox: Cesium.SkyBox.createEarthSkyBox(),
  });
  // Our own click handling replaces Cesium's default double-click "track entity"
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

  const { scene } = viewer;
  const globe = scene.globe;
  globe.baseColor = css('#111');

  if (!body.atmosphere) {
    // No atmosphere, fog, or Earth's Sun/Moon on Mars and the Moon
    globe.showGroundAtmosphere = false;
    globe.enableLighting = false;
    scene.fog.enabled = false;
    if (scene.sun) scene.sun.show = false;
    if (scene.moon) scene.moon.show = false;
  }

  // High-resolution layer, only drawn once the camera is close enough
  if (body.detail) {
    viewer.imageryLayers.add(
      new Cesium.ImageryLayer(body.detail.make(), { minimumTerrainLevel: body.detail.fromLevel }),
    );
  }

  // Relief layer (hidden by default)
  let reliefLayer = null;
  if (body.relief) {
    reliefLayer = viewer.imageryLayers.addImageryProvider(body.relief.make());
    reliefLayer.show = false;
  }

  const toCartesian = (lat, lon, height = 0) => latLonToCartesian(lat, lon, ellipsoid, body.latitudeType, height);

  // --- 2.4 Camera flights ---
  const home = Cesium.Cartesian3.fromDegrees(body.home.lon, body.home.lat, body.home.height, ellipsoid);
  viewer.camera.setView({ destination: home });
  viewer.homeButton.viewModel.command.beforeExecute.addEventListener((e) => {
    e.cancel = true;
    viewer.camera.flyTo({ destination: home, duration: 1.5 });
  });

  /** Fly the camera straight above lat/lon (degrees) at `height` metres above the surface. */
  function flyTo(lat, lon, height = body.flyHeight, duration = 2) {
    return new Promise((resolve) => {
      viewer.camera.flyTo({ destination: toCartesian(lat, lon, height), duration, complete: resolve, cancel: resolve });
    });
  }

  // --- 2.1-2.3 Coordinates: click -> lat/lon, marker, live readout ---
  const toLatLon = (screenPosition) => pickLatLon(viewer, ellipsoid, body.latitudeType, screenPosition);

  const readout = document.createElement('div');
  readout.className = 'coords-readout';
  readout.textContent = '—';
  viewer.container.appendChild(readout);

  const labelStyle = (text) => ({
    text,
    font: '13px system-ui, sans-serif',
    fillColor: Cesium.Color.WHITE,
    showBackground: true,
    backgroundColor: LABEL_BG,
    backgroundPadding: new Cesium.Cartesian2(8, 5),
    pixelOffset: new Cesium.Cartesian2(0, -16),
    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
  });

  let marker = null;
  function setMarker(lat, lon, text = formatLatLon({ lat, lon })) {
    if (marker) viewer.entities.remove(marker);
    marker = viewer.entities.add({
      position: toCartesian(lat, lon, SURFACE_OFFSET),
      point: {
        pixelSize: 11,
        color: COLORS.marker,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
      },
      label: { ...labelStyle(text), pixelOffset: new Cesium.Cartesian2(0, -22) },
    });
  }
  function clearMarker() {
    if (marker) viewer.entities.remove(marker);
    marker = null;
  }

  // --- 2.5 / 2.6 Sites (target sites or known analogs) ---
  const sites = new Cesium.CustomDataSource('sites');
  viewer.dataSources.add(sites);
  let selected = null;

  /**
   * Draw a list of sites: [{ id?, name, lat, lon, subtitle? }].
   * kind = 'target' (Moon/Mars) or 'analog' (Earth); it only changes the colour.
   */
  function setSites(list, kind) {
    sites.entities.removeAll();
    selected = null;
    const color = COLORS[kind] ?? COLORS.target;
    for (const site of list) {
      sites.entities.add({
        id: `${kind}:${site.id ?? site.name}`,
        position: toCartesian(site.lat, site.lon, SURFACE_OFFSET),
        point: {
          pixelSize: SITE_SIZE,
          color,
          outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
          outlineWidth: 1,
        },
        label: {
          ...labelStyle(site.name),
          font: '12px system-ui, sans-serif',
          // Smaller and fainter when far away, so the full globe is not cluttered
          scaleByDistance: new Cesium.NearFarScalar(5e5, 1.0, 1.5e7, 0.65),
          translucencyByDistance: new Cesium.NearFarScalar(5e6, 1.0, 2.5e7, 0.0),
        },
        properties: { site, kind, baseColor: color },
      });
    }
  }

  function styleSite(entity, isSelected) {
    const { baseColor } = entity.properties.getValue(viewer.clock.currentTime);
    entity.point.pixelSize = isSelected ? SELECTED_SIZE : SITE_SIZE;
    entity.point.color = isSelected ? COLORS.selected : baseColor;
    entity.point.outlineColor = isSelected ? Cesium.Color.WHITE : Cesium.Color.BLACK.withAlpha(0.6);
    entity.point.outlineWidth = isSelected ? 2 : 1;
    entity.label.translucencyByDistance = isSelected ? undefined : new Cesium.NearFarScalar(5e6, 1.0, 2.5e7, 0.0);
  }

  /** Highlight a site (by id or entity) and fly to it. */
  function selectSite(idOrEntity, { fly = true } = {}) {
    const entity = typeof idOrEntity === 'string' ? sites.entities.getById(idOrEntity) : idOrEntity;
    if (!entity) return null;
    if (selected && selected !== entity) styleSite(selected, false);
    selected = entity;
    styleSite(entity, true);
    clearMarker();
    const { site } = entity.properties.getValue(viewer.clock.currentTime);
    if (fly) flyTo(site.lat, site.lon);
    return site;
  }

  /** Remove the coordinate marker and un-highlight the selected site. */
  function clearSelection() {
    clearMarker();
    if (selected) styleSite(selected, false);
    selected = null;
  }

  // --- Mouse handling ---
  const pickListeners = [];
  const siteListeners = [];

  const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
  handler.setInputAction((e) => {
    const picked = scene.pick(e.position);
    const entity = picked?.id;
    if (entity && sites.entities.contains(entity)) {
      const site = selectSite(entity);
      siteListeners.forEach((fn) => fn(site));
      return;
    }
    const p = toLatLon(e.position);
    if (!p) return;
    if (selected) styleSite(selected, false);
    selected = null;
    setMarker(p.lat, p.lon);
    pickListeners.forEach((fn) => fn(p));
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  handler.setInputAction((e) => {
    const p = toLatLon(e.endPosition);
    readout.textContent = p ? formatLatLon(p) : '—';
    const overSite = scene.pick(e.endPosition)?.id;
    viewer.canvas.style.cursor = overSite && sites.entities.contains(overSite) ? 'pointer' : '';
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  return {
    viewer,
    body,
    hasRelief: !!reliefLayer,
    setRelief(on) {
      if (reliefLayer) reliefLayer.show = on;
    },
    flyTo,
    /** Put the marker at lat/lon (degrees, in this body's latitude convention). */
    setMarker,
    clearMarker,
    setSites,
    selectSite,
    clearSelection,
    /** fn({ lat, lon }) when the user clicks empty ground. */
    onPick(fn) {
      pickListeners.push(fn);
    },
    /** fn(site) when the user clicks a site. */
    onSiteSelect(fn) {
      siteListeners.push(fn);
    },
    destroy() {
      handler.destroy();
      viewer.destroy();
    },
  };
}
