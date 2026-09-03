(() => {
  "use strict";

  const RAW_BASE =
    "https://raw.githubusercontent.com/IbaadGEO/turkey-ground-motion-risk-model/main";

  const DATA_URLS = {
    boundary: `${RAW_BASE}/data/turkey_boundary.geojson`,
    receivers: `${RAW_BASE}/data/turkey_50km_land_grid_vs30.csv`,
    events:
      `${RAW_BASE}/outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`,
    manifest: "./data/dashboard_manifest.json",
  };

  const SOURCE_ORDER = ["waveform", "isc_ehb", "global_cmt"];
  const MAP_LAYERS = ["vs30", "pga", "loss"];
  const DEFAULT_LAYER = "pga";
  const EXPECTED_RECEIVERS = 311;
  const EXPECTED_SCENARIOS = 321;
  const EXPECTED_FIELDS = [
    "location_id",
    "latitude",
    "longitude",
    "vs30_m_s",
    "median_pga_g",
    "structural_loss_ratio_mean",
    "rhypo_km",
  ];

  const SOURCE_LABELS = {
    waveform: "gWFM",
    isc_ehb: "ISC-EHB",
    global_cmt: "gCMT",
  };

  const SOURCE_COLOURS = {
    waveform: "#3B7A57",
    isc_ehb: "#E69F00",
    global_cmt: "#4C78A8",
  };

  const VIRIDIS = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];
  const LOSS_SCALE = ["#ffffcc", "#fed976", "#fd8d3c", "#e31a1c", "#800026"];
  const ZERO_COLOUR = "#bdbdbd";

  const state = {
    boundary: null,
    receivers: [],
    eventRows: [],
    eventsById: new Map(),
    manifest: null,
    scenarioIndex: new Map(),
    scenarioCache: new Map(),
    map: null,
    boundaryLayer: null,
    thematicLayer: null,
    selectedEventLayer: null,
    otherEventLayer: null,
    eventMarkers: new Map(),
    selectedEventId: null,
    selectedSource: "waveform",
    selectedLayer: DEFAULT_LAYER,
    commonOnly: true,
    scenarioRequestToken: 0,
    currentScenario: null,
    activeScale: null,
    lastScenarioLoad: null,
  };

  const el = {
    loading: document.getElementById("loading-banner"),
    error: document.getElementById("error-banner"),
    eventSelect: document.getElementById("event-select"),
    sourceSelect: document.getElementById("source-select"),
    commonOnly: document.getElementById("common-only"),
    layerInputs: Array.from(
      document.querySelectorAll('input[name="map-variable"]')
    ),
    showEvents: document.getElementById("show-events"),
    fitTurkey: document.getElementById("fit-turkey"),
    scenarioStatus: document.getElementById("scenario-status"),
    mapLegend: document.getElementById("map-legend"),
    statEvents: document.getElementById("stat-events"),
    statCommon: document.getElementById("stat-common"),
    statReceivers: document.getElementById("stat-receivers"),
    statRows: document.getElementById("stat-rows"),
    vulnerabilityCount: document.getElementById("vulnerability-count"),
    eventTitle: document.getElementById("event-title"),
    eventOrigin: document.getElementById("event-origin"),
    eventMagnitude: document.getElementById("event-magnitude"),
    eventCoordinates: document.getElementById("event-coordinates"),
    eventRake: document.getElementById("event-rake"),
    eventCoverage: document.getElementById("event-coverage"),
    sourceBadge: document.getElementById("source-badge"),
    sourceDepthStatus: document.getElementById("source-depth-status"),
    metricDepth: document.getElementById("metric-depth"),
    metricPgaMax: document.getElementById("metric-pga-max"),
    metricPgaMean: document.getElementById("metric-pga-mean"),
    metricLossMax: document.getElementById("metric-loss-max"),
    metricLossMean: document.getElementById("metric-loss-mean"),
    metricRepi: document.getElementById("metric-repi"),
    metricRhypo: document.getElementById("metric-rhypo"),
    metricWithin200: document.getElementById("metric-within200"),
    metricDepthScope: document.getElementById("metric-depth-scope"),
    metricPgaMedian: document.getElementById("metric-pga-median"),
    metricLossMedian: document.getElementById("metric-loss-median"),
    metricLossNonzero: document.getElementById("metric-loss-nonzero"),
    sourceAvailability: document.getElementById("source-availability"),
    shareLink: document.getElementById("share-link"),
  };

  function failInitial(message, error) {
    console.error(message, error);
    el.loading.hidden = true;
    el.error.hidden = false;
    el.error.textContent = message;
  }

  function setScenarioStatus(message, status = "ready") {
    el.scenarioStatus.textContent = message;
    el.scenarioStatus.className = `scenario-status ${status}`;
  }

  async function fetchText(url) {
    const response = await fetch(url, { cache: "default" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}: ${url}`);
    }
    return response.text();
  }

  async function fetchJson(url) {
    const response = await fetch(url, { cache: "default" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}: ${url}`);
    }
    try {
      return await response.json();
    } catch (error) {
      throw new Error(`Malformed JSON at ${url}: ${error.message}`);
    }
  }

  function parseCsv(text) {
    const parsed = Papa.parse(text, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
    });
    if (parsed.errors.length) {
      throw new Error(parsed.errors[0].message);
    }
    return parsed.data;
  }

  function asBoolean(value) {
    if (typeof value === "boolean") return value;
    return String(value).toLowerCase() === "true";
  }

  function formatNumber(value, digits = 2) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
      return "\u2013";
    }
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: digits,
    });
  }

  function formatScientific(value, significantDigits = 3) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "\u2013";
    if (number === 0) return "0";
    if (Math.abs(number) < 0.001) return number.toExponential(significantDigits - 1);
    return Number(number.toPrecision(significantDigits)).toString();
  }

  function formatPga(value) {
    const formatted = formatScientific(value, 3);
    return formatted === "\u2013" ? formatted : `${formatted} g`;
  }

  function formatLoss(value) {
    const formatted = formatScientific(Number(value) * 100, 3);
    return formatted === "\u2013" ? formatted : `${formatted}%`;
  }

  function formatDate(value) {
    if (!value) return "Unknown origin time";
    const parsed = new Date(String(value).replace(" ", "T") + "Z");
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  }

  function scenarioKey(eventId, source) {
    return `${String(eventId)}::${source}`;
  }

  function normaliseLayer(value) {
    return MAP_LAYERS.includes(value) ? value : DEFAULT_LAYER;
  }

  function sourceRowsForEvent(event) {
    const bySource = new Map(event.rows.map((row) => [row.depth_source, row]));
    return SOURCE_ORDER.map((source) => bySource.get(source) || null);
  }

  function buildEvents(rows) {
    const grouped = new Map();
    for (const row of rows) {
      const id = String(row.event_id);
      if (!grouped.has(id)) {
        grouped.set(id, {
          id,
          rows: [],
          origin_time: row.origin_time,
          magnitude: Number(row.magnitude),
          magnitude_type: row.magnitude_type,
          rake: Number(row.rake),
          latitude: Number(row.source_latitude),
          longitude: Number(row.source_longitude),
        });
      }
      grouped.get(id).rows.push(row);
    }
    for (const event of grouped.values()) {
      event.sources = new Set(event.rows.map((row) => row.depth_source));
      event.isCommon = SOURCE_ORDER.every((source) => event.sources.has(source));
    }
    return grouped;
  }

  function validateManifest(manifest) {
    if (!manifest || !Array.isArray(manifest.scenarios)) {
      throw new Error("Dashboard manifest has no scenario list");
    }
    if (
      manifest.scenario_count !== EXPECTED_SCENARIOS ||
      manifest.scenarios.length !== EXPECTED_SCENARIOS
    ) {
      throw new Error(
        `Dashboard manifest must contain ${EXPECTED_SCENARIOS} scenarios`
      );
    }
    if (manifest.receivers_per_scenario !== EXPECTED_RECEIVERS) {
      throw new Error(
        `Dashboard manifest must specify ${EXPECTED_RECEIVERS} receivers per scenario`
      );
    }
    if (JSON.stringify(manifest.receiver_fields) !== JSON.stringify(EXPECTED_FIELDS)) {
      throw new Error("Dashboard manifest receiver fields are not recognised");
    }

    const index = new Map();
    for (const entry of manifest.scenarios) {
      const key = scenarioKey(entry.event_id, entry.depth_source);
      if (
        !SOURCE_ORDER.includes(entry.depth_source) ||
        entry.receiver_count !== EXPECTED_RECEIVERS ||
        typeof entry.path !== "string" ||
        !entry.path.startsWith("data/events/") ||
        !entry.path.endsWith(".json")
      ) {
        throw new Error(`Invalid scenario manifest entry: ${key}`);
      }
      if (index.has(key)) {
        throw new Error(`Duplicate scenario manifest entry: ${key}`);
      }
      index.set(key, entry);
    }
    return index;
  }

  function visibleEvents() {
    const events = Array.from(state.eventsById.values());
    return state.commonOnly ? events.filter((event) => event.isCommon) : events;
  }

  function sortEvents(events) {
    return [...events].sort((a, b) => {
      const magnitudeDifference = b.magnitude - a.magnitude;
      if (Math.abs(magnitudeDifference) > 1e-9) return magnitudeDifference;
      return String(b.origin_time).localeCompare(String(a.origin_time));
    });
  }

  function buildEventOptions() {
    const current = state.selectedEventId;
    const events = sortEvents(visibleEvents());
    el.eventSelect.innerHTML = "";

    for (const event of events) {
      const option = document.createElement("option");
      option.value = event.id;
      const year = String(event.origin_time || "").slice(0, 4);
      option.textContent =
        `${year || "Year ?"} \u00b7 M${formatNumber(event.magnitude, 1)} \u00b7 Event ${event.id}`;
      el.eventSelect.appendChild(option);
    }

    const stillVisible = events.some((event) => event.id === current);
    if (!stillVisible) {
      state.selectedEventId = events.length ? events[0].id : null;
    }
    if (state.selectedEventId) {
      el.eventSelect.value = state.selectedEventId;
    }
  }

  function selectedEvent() {
    return state.eventsById.get(String(state.selectedEventId)) || null;
  }

  function selectedSourceRow(event) {
    if (!event) return null;
    return event.rows.find((row) => row.depth_source === state.selectedSource) || null;
  }

  function vs30Colour(value) {
    const v = Number(value);
    if (v < 300) return "#B44D3C";
    if (v < 500) return "#D98A3A";
    if (v < 700) return "#D8B83F";
    if (v < 900) return "#6F9F62";
    return "#477B96";
  }

  function hexToRgb(hex) {
    const value = hex.replace("#", "");
    return [0, 2, 4].map((offset) => parseInt(value.slice(offset, offset + 2), 16));
  }

  function interpolatePalette(palette, normalised) {
    const clipped = Math.max(0, Math.min(1, Number(normalised)));
    const position = clipped * (palette.length - 1);
    const lower = Math.min(Math.floor(position), palette.length - 2);
    const fraction = position - lower;
    const first = hexToRgb(palette[lower]);
    const second = hexToRgb(palette[lower + 1]);
    const channels = first.map((value, index) =>
      Math.round(value + (second[index] - value) * fraction)
    );
    return `rgb(${channels.join(",")})`;
  }

  function paletteGradient(palette) {
    const stops = palette.map(
      (colour, index) => `${colour} ${(index / (palette.length - 1)) * 100}%`
    );
    return `linear-gradient(to right, ${stops.join(", ")})`;
  }

  function initialiseMap() {
    state.map = L.map("map", {
      zoomControl: true,
      preferCanvas: true,
    }).setView([39.0, 35.1], 6);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(state.map);

    state.boundaryLayer = L.geoJSON(state.boundary, {
      style: {
        color: "#274e5d",
        weight: 1.8,
        opacity: 0.9,
        fillColor: "#7faeb0",
        fillOpacity: 0.08,
      },
    }).addTo(state.map);
    state.thematicLayer = L.layerGroup().addTo(state.map);
    state.otherEventLayer = L.layerGroup();
    state.selectedEventLayer = L.layerGroup().addTo(state.map);
    fitTurkey();
  }

  function fitTurkey() {
    if (state.boundaryLayer) {
      state.map.fitBounds(state.boundaryLayer.getBounds(), { padding: [18, 18] });
    }
  }

  function markerOptions(fillColor) {
    return {
      radius: 4.2,
      color: "#ffffff",
      weight: 0.75,
      fillColor,
      fillOpacity: 0.9,
    };
  }

  function renderVs30Legend() {
    const bins = [
      ["#B44D3C", "<300"],
      ["#D98A3A", "300&ndash;500"],
      ["#D8B83F", "500&ndash;700"],
      ["#6F9F62", "700&ndash;900"],
      ["#477B96", "&ge;900"],
    ];
    el.mapLegend.innerHTML = `
      <strong>Vs30 (m/s)</strong>
      <div class="legend-bins">
        ${bins.map(([colour, label]) =>
          `<i class="legend-swatch" style="background:${colour}"></i><span>${label}</span>`
        ).join("")}
      </div>
      <span class="legend-note">Fixed receiver-site bins.</span>
    `;
    state.activeScale = { layer: "vs30", type: "fixed-bins" };
  }

  function renderGradientLegend({ title, palette, labels, note, zero = false, scale }) {
    el.mapLegend.innerHTML = `
      <strong>${title}</strong>
      ${zero ? `<div class="legend-bins"><i class="legend-swatch" style="background:${ZERO_COLOUR}"></i><span>Exactly zero</span></div>` : ""}
      <div class="legend-gradient" style="background:${paletteGradient(palette)}"></div>
      <div class="legend-labels">${labels.map((label) => `<span>${label}</span>`).join("")}</div>
      <span class="legend-note">${note}</span>
    `;
    state.activeScale = scale;
  }

  function renderUnavailableLegend() {
    const label = state.selectedLayer === "pga" ? "PGA (g)" : "Structural loss ratio (%)";
    el.mapLegend.innerHTML = `
      <strong>${label}</strong>
      <span class="legend-note">Unavailable for this event and depth source.</span>
    `;
    state.activeScale = { layer: state.selectedLayer, type: "unavailable" };
  }

  function renderVs30Receivers() {
    state.thematicLayer.clearLayers();
    state.currentScenario = null;
    for (const receiver of state.receivers) {
      const marker = L.circleMarker(
        [Number(receiver.latitude), Number(receiver.longitude)],
        markerOptions(vs30Colour(receiver.vs30_m_s))
      );
      const status = receiver.vs30_status === "nearest_valid"
        ? `nearest valid (${formatNumber(receiver.fallback_distance_m, 0)} m)`
        : "direct raster cell";
      marker.bindPopup(`
        <div class="popup-title">Receiver ${receiver.location_id}</div>
        <div class="popup-grid">
          <span>Vs30</span><strong>${formatNumber(receiver.vs30_m_s, 1)} m/s</strong>
          <span>Sampling</span><strong>${status}</strong>
        </div>
      `);
      marker.addTo(state.thematicLayer);
    }
    renderVs30Legend();
    el.scenarioStatus.dataset.receiverCount = String(state.receivers.length);
    el.scenarioStatus.dataset.loadSource = "source-independent";
    el.scenarioStatus.dataset.loadMilliseconds = "0";
    setScenarioStatus(`${state.receivers.length} source-independent Vs30 receivers`);
  }

  function decodeScenario(payload, entry) {
    if (!payload || !Array.isArray(payload.receivers)) {
      throw new Error("Scenario JSON has no receiver array");
    }
    if (
      String(payload.event_id) !== String(entry.event_id) ||
      payload.depth_source !== entry.depth_source
    ) {
      throw new Error("Scenario JSON event/source does not match the manifest");
    }
    if (
      payload.receiver_count !== EXPECTED_RECEIVERS ||
      payload.receivers.length !== EXPECTED_RECEIVERS
    ) {
      throw new Error(`Scenario JSON must contain ${EXPECTED_RECEIVERS} receivers`);
    }
    if (JSON.stringify(payload.fields) !== JSON.stringify(EXPECTED_FIELDS)) {
      throw new Error("Scenario JSON fields are not recognised");
    }

    const locations = new Set();
    const receivers = payload.receivers.map((row) => {
      if (!Array.isArray(row) || row.length !== EXPECTED_FIELDS.length) {
        throw new Error("Scenario receiver row has the wrong field count");
      }
      const [locationId, latitude, longitude, vs30, pga, loss, rhypo] = row;
      const numeric = [latitude, longitude, vs30, pga, loss, rhypo].map(Number);
      if (!numeric.every(Number.isFinite)) {
        throw new Error("Scenario receiver row contains non-finite values");
      }
      if (
        numeric[0] < -90 || numeric[0] > 90 ||
        numeric[1] < -180 || numeric[1] > 180 ||
        numeric[2] <= 0 || numeric[3] <= 0 ||
        numeric[4] < 0 || numeric[4] > 1 || numeric[5] < 0
      ) {
        throw new Error("Scenario receiver row is outside its valid range");
      }
      const locationKey = String(locationId);
      if (locations.has(locationKey)) {
        throw new Error(`Duplicate receiver ${locationKey} in scenario JSON`);
      }
      locations.add(locationKey);
      return {
        location_id: locationId,
        latitude: numeric[0],
        longitude: numeric[1],
        vs30_m_s: numeric[2],
        median_pga_g: numeric[3],
        structural_loss_ratio_mean: numeric[4],
        rhypo_km: numeric[5],
      };
    });
    return {
      event_id: String(payload.event_id),
      depth_source: payload.depth_source,
      receivers,
    };
  }

  async function loadScenario(eventId, source) {
    const key = scenarioKey(eventId, source);
    if (state.scenarioCache.has(key)) {
      state.lastScenarioLoad = { key, cached: true, milliseconds: 0 };
      return state.scenarioCache.get(key);
    }
    const entry = state.scenarioIndex.get(key);
    if (!entry) {
      throw new Error("No validated receiver data exist for this event/depth source");
    }
    const start = performance.now();
    const url = new URL(entry.path, window.location.href).toString();
    const payload = await fetchJson(url);
    const scenario = decodeScenario(payload, entry);
    const milliseconds = performance.now() - start;
    state.scenarioCache.set(key, scenario);
    state.lastScenarioLoad = { key, cached: false, milliseconds };
    return scenario;
  }

  function renderPgaScenario(scenario) {
    state.thematicLayer.clearLayers();
    const values = scenario.receivers.map((receiver) => receiver.median_pga_g);
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const logMinimum = Math.log(minimum);
    const logSpan = Math.log(maximum) - logMinimum;
    const scaleValue = (value) =>
      logSpan > 0 ? (Math.log(value) - logMinimum) / logSpan : 0.5;

    for (const receiver of scenario.receivers) {
      const colour = interpolatePalette(VIRIDIS, scaleValue(receiver.median_pga_g));
      const marker = L.circleMarker(
        [receiver.latitude, receiver.longitude],
        markerOptions(colour)
      );
      marker.bindPopup(`
        <div class="popup-title">Receiver ${receiver.location_id}</div>
        <div class="popup-grid">
          <span>PGA</span><strong>${formatPga(receiver.median_pga_g)}</strong>
          <span>Hypocentral distance</span><strong>${formatNumber(receiver.rhypo_km, 1)} km</strong>
          <span>Vs30</span><strong>${formatNumber(receiver.vs30_m_s, 1)} m/s</strong>
        </div>
      `);
      marker.addTo(state.thematicLayer);
    }

    const middle = Math.sqrt(minimum * maximum);
    renderGradientLegend({
      title: "PGA (g)",
      palette: VIRIDIS,
      labels: [minimum, middle, maximum].map((value) => formatScientific(value, 2)),
      note: "Event-specific logarithmic scale; min, geometric midpoint and max shown.",
      scale: { layer: "pga", type: "log", minimum, maximum },
    });
  }

  function renderLossScenario(scenario) {
    state.thematicLayer.clearLayers();
    const values = scenario.receivers.map(
      (receiver) => receiver.structural_loss_ratio_mean
    );
    const maximum = Math.max(...values);

    for (const receiver of scenario.receivers) {
      const loss = receiver.structural_loss_ratio_mean;
      const colour = loss === 0
        ? ZERO_COLOUR
        : interpolatePalette(LOSS_SCALE, maximum > 0 ? loss / maximum : 0);
      const marker = L.circleMarker(
        [receiver.latitude, receiver.longitude],
        markerOptions(colour)
      );
      marker.bindPopup(`
        <div class="popup-title">Receiver ${receiver.location_id}</div>
        <div class="popup-grid">
          <span>Structural loss ratio</span><strong>${formatLoss(loss)}</strong>
          <span>PGA</span><strong>${formatPga(receiver.median_pga_g)}</strong>
        </div>
      `);
      marker.addTo(state.thematicLayer);
    }

    if (maximum === 0) {
      el.mapLegend.innerHTML = `
        <strong>Structural loss ratio (%)</strong>
        <div class="legend-bins"><i class="legend-swatch" style="background:${ZERO_COLOUR}"></i><span>All receivers: 0%</span></div>
        <span class="legend-note">No non-zero structural loss ratio for this scenario.</span>
      `;
      state.activeScale = { layer: "loss", type: "all-zero", minimum: 0, maximum: 0 };
      return;
    }

    renderGradientLegend({
      title: "Structural loss ratio (%)",
      palette: LOSS_SCALE,
      labels: [0, maximum * 50, maximum * 100].map((value) =>
        `${formatScientific(value, 2)}%`
      ),
      note: "Linear event-specific scale for positive ratios; zero is grey.",
      zero: true,
      scale: { layer: "loss", type: "linear", minimum: 0, maximum },
    });
  }

  async function renderThematicLayer() {
    const requestToken = ++state.scenarioRequestToken;
    if (state.selectedLayer === "vs30") {
      renderVs30Receivers();
      return;
    }

    const event = selectedEvent();
    const row = selectedSourceRow(event);
    state.thematicLayer.clearLayers();
    state.currentScenario = null;
    if (!event || !row) {
      el.scenarioStatus.dataset.receiverCount = "0";
      el.scenarioStatus.dataset.loadSource = "unavailable";
      el.scenarioStatus.dataset.loadMilliseconds = "0";
      renderUnavailableLegend();
      setScenarioStatus("Selected depth source is unavailable for this event", "error");
      return;
    }

    setScenarioStatus("Loading selected receiver field\u2026", "loading");
    el.scenarioStatus.dataset.receiverCount = "0";
    el.scenarioStatus.dataset.loadSource = "loading";
    el.scenarioStatus.dataset.loadMilliseconds = "0";
    try {
      const scenario = await loadScenario(event.id, state.selectedSource);
      if (requestToken !== state.scenarioRequestToken) return;
      state.currentScenario = scenario;
      if (state.selectedLayer === "pga") {
        renderPgaScenario(scenario);
      } else {
        renderLossScenario(scenario);
      }
      el.scenarioStatus.dataset.receiverCount = String(scenario.receivers.length);
      const load = state.lastScenarioLoad;
      el.scenarioStatus.dataset.loadSource = load.cached ? "cache" : "network";
      el.scenarioStatus.dataset.loadMilliseconds = load.milliseconds.toFixed(1);
      const detail = load.cached
        ? "reused from browser cache"
        : `loaded in ${formatNumber(load.milliseconds, 0)} ms`;
      setScenarioStatus(`${scenario.receivers.length} receivers \u00b7 ${detail}`);
    } catch (error) {
      if (requestToken !== state.scenarioRequestToken) return;
      state.thematicLayer.clearLayers();
      state.currentScenario = null;
      el.scenarioStatus.dataset.receiverCount = "0";
      el.scenarioStatus.dataset.loadSource = "error";
      el.scenarioStatus.dataset.loadMilliseconds = "0";
      renderUnavailableLegend();
      setScenarioStatus(`Receiver data unavailable: ${error.message}`, "error");
      console.error("Receiver scenario loading failed", error);
    }
  }

  function eventMarkerRadius(event, selected = false) {
    const magnitudeRadius = Math.max(4, 4 + (event.magnitude - 5) * 2.1);
    return selected ? Math.max(6, magnitudeRadius + 1) : Math.max(3, magnitudeRadius * 0.68);
  }

  function eventTooltip(event) {
    const row = event.rows.find((item) => item.depth_source === state.selectedSource);
    const loss = row ? formatLoss(row.maximum_structural_loss_ratio) : "unavailable";
    return `M${formatNumber(event.magnitude, 1)} \u00b7 Event ${event.id}<br>${SOURCE_LABELS[state.selectedSource]} max loss: ${loss}`;
  }

  function renderEvents() {
    state.selectedEventLayer.clearLayers();
    state.otherEventLayer.clearLayers();
    state.eventMarkers.clear();
    for (const event of visibleEvents()) {
      const selected = event.id === state.selectedEventId;
      const marker = L.circleMarker([event.latitude, event.longitude], {
        radius: eventMarkerRadius(event, selected),
        color: selected ? "#0b2934" : "#ffffff",
        weight: selected ? 3 : 0.8,
        fillColor: selected ? "#d45b3f" : "#7d5551",
        fillOpacity: selected ? 0.98 : 0.38,
      });
      marker.bindTooltip(eventTooltip(event), { direction: "top", offset: [0, -4] });
      marker.on("click", () => selectEvent(event.id, true));
      marker.addTo(selected ? state.selectedEventLayer : state.otherEventLayer);
      state.eventMarkers.set(event.id, marker);
    }
    updateEventLayerVisibility();
  }

  function updateEventLayerVisibility() {
    if (!state.map || !state.selectedEventLayer || !state.otherEventLayer) return;
    if (!state.map.hasLayer(state.selectedEventLayer)) {
      state.selectedEventLayer.addTo(state.map);
    }
    if (el.showEvents.checked) {
      if (!state.map.hasLayer(state.otherEventLayer)) {
        state.otherEventLayer.addTo(state.map);
      }
    } else if (state.map.hasLayer(state.otherEventLayer)) {
      state.map.removeLayer(state.otherEventLayer);
    }
    state.selectedEventLayer.eachLayer((marker) => marker.bringToFront());
  }

  function sourceBadgeStyle(source) {
    const colour = SOURCE_COLOURS[source] || "#5e6a72";
    el.sourceBadge.style.color = colour;
    el.sourceBadge.style.border = `1px solid ${colour}33`;
    el.sourceBadge.style.background = `${colour}14`;
  }

  function setMetricElements(row) {
    const metricElements = [
      el.metricPgaMax,
      el.metricPgaMean,
      el.metricLossMax,
      el.metricLossMean,
      el.metricRepi,
      el.metricRhypo,
      el.metricWithin200,
      el.metricDepthScope,
      el.metricPgaMedian,
      el.metricLossMedian,
      el.metricLossNonzero,
    ];
    if (!row) {
      el.metricDepth.textContent = "\u2013";
      metricElements.forEach((element) => { element.textContent = "\u2013"; });
      return;
    }

    el.metricDepth.textContent = `${formatNumber(row.source_depth_km, 2)} km`;
    el.metricPgaMax.textContent = formatPga(row.maximum_pga_g);
    el.metricPgaMean.textContent = formatPga(row.mean_pga_g);
    el.metricLossMax.textContent = formatLoss(row.maximum_structural_loss_ratio);
    el.metricLossMean.textContent = formatLoss(row.mean_structural_loss_ratio);
    el.metricRepi.textContent = `${formatNumber(row.minimum_repi_km, 1)} km`;
    el.metricRhypo.textContent = `${formatNumber(row.minimum_rhypo_km, 1)} km`;
    el.metricWithin200.textContent =
      `${formatNumber(row.receivers_within_200_km, 0)} / ${formatNumber(row.receiver_count, 0)}`;
    el.metricDepthScope.textContent = asBoolean(row.source_within_30_km)
      ? "Within 30 km applicability check"
      : "Deeper than 30 km applicability check";
    el.metricPgaMedian.textContent = formatPga(row.median_pga_g);
    el.metricLossMedian.textContent = formatLoss(row.median_structural_loss_ratio);
    el.metricLossNonzero.textContent =
      `${formatNumber(row.locations_with_nonzero_structural_loss, 0)} / ${formatNumber(row.receiver_count, 0)}`;
  }

  function updateEventDetails() {
    const event = selectedEvent();
    if (!event) return;
    const row = selectedSourceRow(event);

    el.eventTitle.textContent = `M${formatNumber(event.magnitude, 1)} event ${event.id}`;
    el.eventOrigin.textContent = formatDate(event.origin_time);
    el.eventMagnitude.textContent =
      `${event.magnitude_type || "M"} ${formatNumber(event.magnitude, 1)}`;
    el.eventCoordinates.textContent =
      `${formatNumber(event.latitude, 3)}, ${formatNumber(event.longitude, 3)}`;
    el.eventRake.textContent = Number.isFinite(event.rake)
      ? `${formatNumber(event.rake, 1)}\u00b0`
      : "\u2013";
    el.eventCoverage.textContent = `${event.sources.size}/3 sources`;
    el.sourceBadge.textContent = SOURCE_LABELS[state.selectedSource];
    sourceBadgeStyle(state.selectedSource);
    el.sourceDepthStatus.textContent = row
      ? (asBoolean(row.source_within_30_km)
        ? "Within 30 km depth check"
        : "Beyond 30 km depth check")
      : "Unavailable for this event";
    setMetricElements(row);

    el.sourceAvailability.innerHTML = "";
    for (const source of SOURCE_ORDER) {
      const pill = document.createElement("span");
      const available = event.sources.has(source);
      pill.className = `availability-pill${available ? " available" : ""}`;
      pill.textContent = `${SOURCE_LABELS[source]} ${available ? "available" : "missing"}`;
      el.sourceAvailability.appendChild(pill);
    }

    const url = new URL(window.location.href);
    url.searchParams.set("event", event.id);
    url.searchParams.set("source", state.selectedSource);
    url.searchParams.set("layer", state.selectedLayer);
    el.shareLink.href = url.toString();
  }

  function chartLayout(yTitle, options = {}) {
    const layout = {
      margin: { l: 58, r: 12, t: options.legend ? 42 : 18, b: 44 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      showlegend: Boolean(options.legend),
      barmode: options.legend ? "group" : "relative",
      bargap: 0.24,
      legend: {
        orientation: "h",
        x: 0,
        y: 1.16,
        font: { size: 10 },
      },
      font: {
        family: 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
        color: "#34434f",
        size: 11,
      },
      xaxis: { fixedrange: true, tickfont: { size: 11 } },
      yaxis: {
        title: yTitle,
        fixedrange: true,
        gridcolor: "#e4e9ed",
        zerolinecolor: "#cfd7dc",
      },
    };
    if (options.depthLine) {
      layout.shapes = [{
        type: "line",
        xref: "paper",
        x0: 0,
        x1: 1,
        yref: "y",
        y0: 30,
        y1: 30,
        line: { color: "#626b71", width: 1.4, dash: "dash" },
      }];
      layout.annotations = [{
        xref: "paper",
        x: 0.98,
        yref: "y",
        y: 30,
        text: "30 km",
        showarrow: false,
        xanchor: "right",
        yanchor: "bottom",
        font: { size: 9, color: "#626b71" },
      }];
    }
    return layout;
  }

  function renderCharts() {
    const event = selectedEvent();
    if (!event) return;
    const rows = sourceRowsForEvent(event);
    const x = SOURCE_ORDER.map((source) => SOURCE_LABELS[source]);
    const sourceColours = SOURCE_ORDER.map((source) => SOURCE_COLOURS[source]);
    const depth = rows.map((row) => row ? Number(row.source_depth_km) : null);
    const pgaMaximum = rows.map((row) => row ? Number(row.maximum_pga_g) : null);
    const pgaMean = rows.map((row) => row ? Number(row.mean_pga_g) : null);
    const lossMaximum = rows.map((row) =>
      row ? Number(row.maximum_structural_loss_ratio) * 100 : null
    );
    const lossMean = rows.map((row) =>
      row ? Number(row.mean_structural_loss_ratio) * 100 : null
    );
    const config = { displayModeBar: false, responsive: true };

    Plotly.react("depth-chart", [{
      type: "bar",
      x,
      y: depth,
      marker: { color: sourceColours, line: { color: "#ffffff", width: 0.8 } },
      hovertemplate: "%{x}<br>%{y:.2f} km<extra></extra>",
    }], chartLayout("Depth (km)", { depthLine: true }), config);

    const comparisonTraces = (maximum, mean, unit) => [
      {
        type: "bar",
        name: "Maximum",
        x,
        y: maximum,
        marker: { color: "#1f6075", line: { color: "#174858", width: 0.7 } },
        hovertemplate: `%{x}<br>Maximum: %{y:.4g} ${unit}<extra></extra>`,
      },
      {
        type: "scatter",
        mode: "markers",
        name: "Mean",
        x,
        y: mean,
        marker: {
          color: "#e69f00",
          symbol: "diamond",
          size: 11,
          line: { color: "#6f4700", width: 1.2 },
        },
        hovertemplate: `%{x}<br>Mean: %{y:.4g} ${unit}<extra></extra>`,
      },
    ];

    Plotly.react(
      "pga-chart",
      comparisonTraces(pgaMaximum, pgaMean, "g"),
      chartLayout("PGA (g)", { legend: true }),
      config
    );
    Plotly.react(
      "loss-chart",
      comparisonTraces(lossMaximum, lossMean, "%"),
      chartLayout("Structural loss ratio (%)", { legend: true }),
      config
    );
  }

  function updateUrl() {
    const url = new URL(window.location.href);
    if (state.selectedEventId) url.searchParams.set("event", state.selectedEventId);
    url.searchParams.set("source", state.selectedSource);
    url.searchParams.set("layer", state.selectedLayer);
    window.history.replaceState({}, "", url);
    el.shareLink.href = url.toString();
  }

  function selectEvent(eventId, pan = false) {
    if (!state.eventsById.has(String(eventId))) return;
    state.selectedEventId = String(eventId);
    el.eventSelect.value = state.selectedEventId;
    renderEvents();
    updateEventDetails();
    renderCharts();
    updateUrl();
    void renderThematicLayer();

    const event = selectedEvent();
    if (pan && event) {
      state.map.flyTo(
        [event.latitude, event.longitude],
        Math.max(state.map.getZoom(), 7),
        { duration: 0.7 }
      );
    }
  }

  function applySource(source) {
    if (!SOURCE_ORDER.includes(source)) return;
    state.selectedSource = source;
    el.sourceSelect.value = source;
    renderEvents();
    updateEventDetails();
    updateUrl();
    void renderThematicLayer();
  }

  function applyLayer(layer) {
    state.selectedLayer = normaliseLayer(layer);
    for (const input of el.layerInputs) {
      input.checked = input.value === state.selectedLayer;
    }
    updateEventDetails();
    updateUrl();
    void renderThematicLayer();
  }

  function populateStats() {
    const events = Array.from(state.eventsById.values());
    const common = events.filter((event) => event.isCommon);
    el.statEvents.textContent = events.length.toLocaleString();
    el.statCommon.textContent = common.length.toLocaleString();
    el.statReceivers.textContent = state.receivers.length.toLocaleString();
    el.statRows.textContent = state.manifest.scenario_count.toLocaleString();
    el.vulnerabilityCount.textContent =
      state.manifest.vulnerability.function_count.toLocaleString();
  }

  function setInitialSelection() {
    const params = new URLSearchParams(window.location.search);
    const requestedEvent = params.get("event");
    const requestedSource = params.get("source");
    state.selectedLayer = normaliseLayer(params.get("layer"));

    if (requestedSource && SOURCE_ORDER.includes(requestedSource)) {
      state.selectedSource = requestedSource;
    }
    if (requestedEvent && state.eventsById.has(String(requestedEvent))) {
      const event = state.eventsById.get(String(requestedEvent));
      if (!event.isCommon) {
        state.commonOnly = false;
        el.commonOnly.checked = false;
      }
      state.selectedEventId = String(requestedEvent);
    }

    el.sourceSelect.value = state.selectedSource;
    for (const input of el.layerInputs) {
      input.checked = input.value === state.selectedLayer;
    }
    buildEventOptions();
    selectEvent(state.selectedEventId, false);
  }

  function bindControls() {
    el.eventSelect.addEventListener("change", (event) => {
      selectEvent(event.target.value, true);
    });
    el.sourceSelect.addEventListener("change", (event) => {
      applySource(event.target.value);
    });
    el.commonOnly.addEventListener("change", () => {
      state.commonOnly = el.commonOnly.checked;
      buildEventOptions();
      renderEvents();
      selectEvent(state.selectedEventId, false);
    });
    for (const input of el.layerInputs) {
      input.addEventListener("change", (event) => {
        if (event.target.checked) applyLayer(event.target.value);
      });
    }
    el.showEvents.addEventListener("change", updateEventLayerVisibility);
    el.fitTurkey.addEventListener("click", fitTurkey);
  }

  function installDebugInterface() {
    window.DashboardDebug = Object.freeze({
      getState: () => ({
        selectedEventId: state.selectedEventId,
        selectedSource: state.selectedSource,
        selectedLayer: state.selectedLayer,
        commonOnly: state.commonOnly,
        eventCount: state.eventsById.size,
        scenarioCount: state.scenarioIndex.size,
        thematicMarkerCount: state.thematicLayer.getLayers().length,
        selectedEventMarkerCount: state.selectedEventLayer.getLayers().length,
        otherEventMarkerCount: state.otherEventLayer.getLayers().length,
        showAllEarthquakeLocations: el.showEvents.checked,
        cacheSize: state.scenarioCache.size,
        currentScenarioKey: state.currentScenario
          ? scenarioKey(state.currentScenario.event_id, state.currentScenario.depth_source)
          : null,
        activeScale: state.activeScale,
        lastScenarioLoad: state.lastScenarioLoad,
      }),
      normaliseLayer,
      formatPga,
      formatLoss,
      scenarioKey,
    });
  }

  async function initialise() {
    try {
      const [boundaryText, receiverText, eventText, manifest] = await Promise.all([
        fetchText(DATA_URLS.boundary),
        fetchText(DATA_URLS.receivers),
        fetchText(DATA_URLS.events),
        fetchJson(DATA_URLS.manifest),
      ]);

      state.boundary = JSON.parse(boundaryText);
      state.receivers = parseCsv(receiverText);
      state.eventRows = parseCsv(eventText);
      state.eventsById = buildEvents(state.eventRows);
      state.manifest = manifest;
      state.scenarioIndex = validateManifest(manifest);

      if (state.receivers.length !== EXPECTED_RECEIVERS) {
        throw new Error(`Expected ${EXPECTED_RECEIVERS} production receivers`);
      }
      if (state.eventsById.size !== 117 || state.eventRows.length !== EXPECTED_SCENARIOS) {
        throw new Error("Event summary does not contain the expected 117 events / 321 scenarios");
      }

      initialiseMap();
      populateStats();
      bindControls();
      setInitialSelection();
      installDebugInterface();
      el.loading.hidden = true;
    } catch (error) {
      failInitial(
        "The dashboard could not load its validated repository data. Check the browser console for details.",
        error
      );
    }
  }

  initialise();
})();
