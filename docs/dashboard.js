(() => {
  "use strict";

  const RAW_BASE =
    "https://raw.githubusercontent.com/IbaadGEO/turkey-ground-motion-risk-model/main";

  const DATA_URLS = {
    boundary: `${RAW_BASE}/data/turkey_boundary.geojson`,
    receivers: `${RAW_BASE}/data/turkey_50km_land_grid_vs30.csv`,
    events:
      `${RAW_BASE}/outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`,
  };

  const SOURCE_ORDER = ["waveform", "isc_ehb", "global_cmt"];

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

  const state = {
    boundary: null,
    receivers: [],
    eventRows: [],
    eventsById: new Map(),
    map: null,
    boundaryLayer: null,
    receiverLayer: null,
    eventLayer: null,
    eventMarkers: new Map(),
    selectedEventId: null,
    selectedSource: "waveform",
    commonOnly: true,
  };

  const el = {
    loading: document.getElementById("loading-banner"),
    error: document.getElementById("error-banner"),
    eventSelect: document.getElementById("event-select"),
    sourceSelect: document.getElementById("source-select"),
    commonOnly: document.getElementById("common-only"),
    showReceivers: document.getElementById("show-receivers"),
    showEvents: document.getElementById("show-events"),
    fitTurkey: document.getElementById("fit-turkey"),
    statEvents: document.getElementById("stat-events"),
    statCommon: document.getElementById("stat-common"),
    statReceivers: document.getElementById("stat-receivers"),
    statRows: document.getElementById("stat-rows"),
    eventTitle: document.getElementById("event-title"),
    eventOrigin: document.getElementById("event-origin"),
    eventMagnitude: document.getElementById("event-magnitude"),
    eventCoordinates: document.getElementById("event-coordinates"),
    eventRake: document.getElementById("event-rake"),
    eventCoverage: document.getElementById("event-coverage"),
    sourceBadge: document.getElementById("source-badge"),
    sourceDepthStatus: document.getElementById("source-depth-status"),
    metricDepth: document.getElementById("metric-depth"),
    metricPga: document.getElementById("metric-pga"),
    metricLoss: document.getElementById("metric-loss"),
    metricRhypo: document.getElementById("metric-rhypo"),
    metricWithin200: document.getElementById("metric-within200"),
    sourceAvailability: document.getElementById("source-availability"),
    shareLink: document.getElementById("share-link"),
  };

  function fail(message, error) {
    console.error(message, error);
    el.loading.hidden = true;
    el.error.hidden = false;
    el.error.textContent = message;
  }

  async function fetchText(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}: ${url}`);
    }
    return response.text();
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
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "\u2013";
    }
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: digits,
    });
  }

  function formatScientific(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "\u2013";
    if (number === 0) return "0";
    if (Math.abs(number) < 0.001) return number.toExponential(2);
    return number.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
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
      event.isCommon = SOURCE_ORDER.every((source) =>
        event.sources.has(source)
      );
    }

    return grouped;
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
    if (stillVisible) {
      state.selectedEventId = current;
    } else if (events.length) {
      state.selectedEventId = events[0].id;
    }

    if (state.selectedEventId) {
      el.eventSelect.value = state.selectedEventId;
    }
  }

  function vs30Colour(value) {
    const v = Number(value);
    if (v < 300) return "#B44D3C";
    if (v < 500) return "#D98A3A";
    if (v < 700) return "#D8B83F";
    if (v < 900) return "#6F9F62";
    return "#477B96";
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

    state.receiverLayer = L.layerGroup().addTo(state.map);
    state.eventLayer = L.layerGroup().addTo(state.map);

    fitTurkey();
  }

  function fitTurkey() {
    if (state.boundaryLayer) {
      state.map.fitBounds(state.boundaryLayer.getBounds(), {
        padding: [18, 18],
      });
    }
  }

  function renderReceivers() {
    state.receiverLayer.clearLayers();

    for (const receiver of state.receivers) {
      const colour = vs30Colour(receiver.vs30_m_s);
      const marker = L.circleMarker(
        [Number(receiver.latitude), Number(receiver.longitude)],
        {
          radius: 4,
          color: "#ffffff",
          weight: 0.7,
          fillColor: colour,
          fillOpacity: 0.86,
        }
      );

      const fallback =
        receiver.vs30_status === "nearest_valid"
          ? `${formatNumber(receiver.fallback_distance_m, 0)} m`
          : "Not used";

      marker.bindPopup(`
        <div class="popup-title">Receiver ${receiver.location_id}</div>
        <div class="popup-grid">
          <span>Vs30</span><strong>${formatNumber(receiver.vs30_m_s, 1)} m/s</strong>
          <span>Status</span><strong>${receiver.vs30_status || "\u2013"}</strong>
          <span>Fallback</span><strong>${fallback}</strong>
          <span>Latitude</span><strong>${formatNumber(receiver.latitude, 4)}</strong>
          <span>Longitude</span><strong>${formatNumber(receiver.longitude, 4)}</strong>
        </div>
      `);

      marker.addTo(state.receiverLayer);
    }
  }

  function eventMarkerRadius(event, selected = false) {
    const magnitudeRadius = Math.max(4, 4 + (event.magnitude - 5) * 2.1);
    return selected
      ? Math.max(6, magnitudeRadius + 1.0)
      : Math.max(3, magnitudeRadius * 0.68);
  }

  function renderEvents() {
    state.eventLayer.clearLayers();
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

      marker.bindTooltip(
        `M${formatNumber(event.magnitude, 1)} \u00b7 Event ${event.id}`,
        { direction: "top", offset: [0, -4] }
      );

      marker.on("click", () => {
        selectEvent(event.id, true);
      });

      marker.addTo(state.eventLayer);
      state.eventMarkers.set(event.id, marker);
    }
  }

  function updateLayerVisibility() {
    if (el.showReceivers.checked) {
      if (!state.map.hasLayer(state.receiverLayer)) {
        state.receiverLayer.addTo(state.map);
      }
    } else if (state.map.hasLayer(state.receiverLayer)) {
      state.map.removeLayer(state.receiverLayer);
    }

    if (el.showEvents.checked) {
      if (!state.map.hasLayer(state.eventLayer)) {
        state.eventLayer.addTo(state.map);
      }
    } else if (state.map.hasLayer(state.eventLayer)) {
      state.map.removeLayer(state.eventLayer);
    }
  }

  function selectedEvent() {
    return state.eventsById.get(String(state.selectedEventId)) || null;
  }

  function selectedSourceRow(event) {
    if (!event) return null;
    return (
      event.rows.find((row) => row.depth_source === state.selectedSource) || null
    );
  }

  function sourceBadgeStyle(source) {
    const colour = SOURCE_COLOURS[source] || "#5e6a72";
    el.sourceBadge.style.color = colour;
    el.sourceBadge.style.border = `1px solid ${colour}33`;
    el.sourceBadge.style.background = `${colour}14`;
  }

  function updateEventDetails() {
    const event = selectedEvent();
    if (!event) return;

    const row = selectedSourceRow(event);

    el.eventTitle.textContent =
      `M${formatNumber(event.magnitude, 1)} event ${event.id}`;
    el.eventOrigin.textContent = formatDate(event.origin_time);
    el.eventMagnitude.textContent =
      `${event.magnitude_type || "M"} ${formatNumber(event.magnitude, 1)}`;
    el.eventCoordinates.textContent =
      `${formatNumber(event.latitude, 3)}, ${formatNumber(event.longitude, 3)}`;
    el.eventRake.textContent =
      Number.isFinite(event.rake) ? `${formatNumber(event.rake, 1)}\u00b0` : "\u2013";
    el.eventCoverage.textContent =
      `${event.sources.size}/3 sources`;

    el.sourceBadge.textContent = SOURCE_LABELS[state.selectedSource];
    sourceBadgeStyle(state.selectedSource);

    if (!row) {
      el.sourceDepthStatus.textContent = "No value for this event";
      el.metricDepth.textContent = "\u2013";
      el.metricPga.textContent = "\u2013";
      el.metricLoss.textContent = "\u2013";
      el.metricRhypo.textContent = "\u2013";
      el.metricWithin200.textContent = "\u2013";
    } else {
      const within30 = asBoolean(row.source_within_30_km);
      el.sourceDepthStatus.textContent = within30
        ? "Within 30 km GMPE depth range"
        : "Deeper than 30 km GMPE depth range";
      el.metricDepth.textContent =
        `${formatNumber(row.source_depth_km, 2)} km`;
      el.metricPga.textContent =
        `${formatScientific(row.maximum_pga_g)} g`;
      el.metricLoss.textContent =
        `${formatScientific(Number(row.maximum_structural_loss_ratio) * 100)}%`;
      el.metricRhypo.textContent =
        `${formatNumber(row.minimum_rhypo_km, 1)} km`;
      el.metricWithin200.textContent =
        `${formatNumber(row.receivers_within_200_km, 0)} / ${formatNumber(row.receiver_count, 0)}`;
    }

    el.sourceAvailability.innerHTML = "";
    for (const source of SOURCE_ORDER) {
      const pill = document.createElement("span");
      const available = event.sources.has(source);
      pill.className =
        "availability-pill" + (available ? " available" : "");
      pill.textContent =
        `${SOURCE_LABELS[source]} ${available ? "available" : "missing"}`;
      el.sourceAvailability.appendChild(pill);
    }

    const url = new URL(window.location.href);
    url.searchParams.set("event", event.id);
    url.searchParams.set("source", state.selectedSource);
    el.shareLink.href = url.toString();
  }

  function chartLayout(yTitle, options = {}) {
    const layout = {
      margin: { l: 58, r: 15, t: 18, b: 44 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      showlegend: false,
      font: {
        family:
          'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
        color: "#34434f",
        size: 11,
      },
      xaxis: {
        fixedrange: true,
        tickfont: { size: 11 },
      },
      yaxis: {
        title: yTitle,
        fixedrange: true,
        gridcolor: "#e4e9ed",
        zerolinecolor: "#cfd7dc",
      },
    };

    if (options.log) {
      layout.yaxis.type = "log";
    }

    if (options.depthLine) {
      layout.shapes = [
        {
          type: "line",
          xref: "paper",
          x0: 0,
          x1: 1,
          yref: "y",
          y0: 30,
          y1: 30,
          line: {
            color: "#626b71",
            width: 1.4,
            dash: "dash",
          },
        },
      ];
      layout.annotations = [
        {
          xref: "paper",
          x: 0.98,
          yref: "y",
          y: 30,
          text: "30 km",
          showarrow: false,
          xanchor: "right",
          yanchor: "bottom",
          font: { size: 9, color: "#626b71" },
        },
      ];
    }

    return layout;
  }

  function renderCharts() {
    const event = selectedEvent();
    if (!event) return;

    const rows = sourceRowsForEvent(event);
    const x = SOURCE_ORDER.map((source) => SOURCE_LABELS[source]);
    const colours = SOURCE_ORDER.map((source) => SOURCE_COLOURS[source]);

    const depth = rows.map((row) =>
      row ? Number(row.source_depth_km) : null
    );
    const pga = rows.map((row) =>
      row ? Number(row.maximum_pga_g) : null
    );
    const loss = rows.map((row) =>
      row ? Number(row.maximum_structural_loss_ratio) * 100 : null
    );

    const commonTrace = (y, hoverTemplate) => ({
      type: "bar",
      x,
      y,
      marker: {
        color: colours,
        line: { color: "#ffffff", width: 0.8 },
      },
      hovertemplate: hoverTemplate + "<extra></extra>",
    });

    const config = {
      displayModeBar: false,
      responsive: true,
    };

    Plotly.react(
      "depth-chart",
      [commonTrace(depth, "%{x}<br>%{y:.2f} km")],
      chartLayout("Depth (km)", { depthLine: true }),
      config
    );

    Plotly.react(
      "pga-chart",
      [commonTrace(pga, "%{x}<br>%{y:.4g} g")],
      chartLayout("Maximum PGA (g)"),
      config
    );

    Plotly.react(
      "loss-chart",
      [commonTrace(loss, "%{x}<br>%{y:.4g}%")],
      chartLayout("Maximum loss (%)"),
      config
    );
  }

  function highlightSelectedEvent() {
    for (const [id, marker] of state.eventMarkers.entries()) {
      const event = state.eventsById.get(id);
      const selected = id === state.selectedEventId;
      marker.setStyle({
        radius: eventMarkerRadius(event, selected),
        color: selected ? "#0b2934" : "#ffffff",
        weight: selected ? 3 : 0.8,
        fillColor: selected ? "#d45b3f" : "#7d5551",
        fillOpacity: selected ? 0.98 : 0.38,
      });
    }
  }

  function updateUrl() {
    const url = new URL(window.location.href);
    if (state.selectedEventId) {
      url.searchParams.set("event", state.selectedEventId);
    }
    url.searchParams.set("source", state.selectedSource);
    window.history.replaceState({}, "", url);
  }

  function selectEvent(eventId, pan = false) {
    if (!state.eventsById.has(String(eventId))) return;

    state.selectedEventId = String(eventId);
    el.eventSelect.value = state.selectedEventId;

    highlightSelectedEvent();
    updateEventDetails();
    renderCharts();
    updateUrl();

    const event = selectedEvent();
    if (pan && event) {
      state.map.flyTo([event.latitude, event.longitude], Math.max(state.map.getZoom(), 7), {
        duration: 0.7,
      });
    }
  }

  function applySource(source) {
    if (!SOURCE_ORDER.includes(source)) return;
    state.selectedSource = source;
    el.sourceSelect.value = source;
    updateEventDetails();
    renderCharts();
    updateUrl();
  }

  function populateStats() {
    const events = Array.from(state.eventsById.values());
    const common = events.filter((event) => event.isCommon);
    el.statEvents.textContent = events.length.toLocaleString();
    el.statCommon.textContent = common.length.toLocaleString();
    el.statReceivers.textContent = state.receivers.length.toLocaleString();
    el.statRows.textContent = state.eventRows.length.toLocaleString();
  }

  function setInitialSelection() {
    const params = new URLSearchParams(window.location.search);
    const requestedEvent = params.get("event");
    const requestedSource = params.get("source");

    if (
      requestedSource &&
      SOURCE_ORDER.includes(requestedSource)
    ) {
      state.selectedSource = requestedSource;
      el.sourceSelect.value = requestedSource;
    }

    buildEventOptions();

    const requestedExists =
      requestedEvent && state.eventsById.has(String(requestedEvent));
    const requestedVisible =
      requestedExists &&
      (!state.commonOnly ||
        state.eventsById.get(String(requestedEvent)).isCommon);

    if (requestedVisible) {
      state.selectedEventId = String(requestedEvent);
      el.eventSelect.value = state.selectedEventId;
    }

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

    el.showReceivers.addEventListener("change", updateLayerVisibility);
    el.showEvents.addEventListener("change", updateLayerVisibility);
    el.fitTurkey.addEventListener("click", fitTurkey);
  }

  async function initialise() {
    try {
      const [boundaryText, receiverText, eventText] = await Promise.all([
        fetchText(DATA_URLS.boundary),
        fetchText(DATA_URLS.receivers),
        fetchText(DATA_URLS.events),
      ]);

      state.boundary = JSON.parse(boundaryText);
      state.receivers = parseCsv(receiverText);
      state.eventRows = parseCsv(eventText);
      state.eventsById = buildEvents(state.eventRows);

      initialiseMap();
      renderReceivers();
      populateStats();
      bindControls();
      setInitialSelection();
      renderEvents();
      highlightSelectedEvent();
      updateLayerVisibility();

      el.loading.hidden = true;
    } catch (error) {
      fail(
        "The dashboard could not load the repository data. Check the browser console for details.",
        error
      );
    }
  }

  initialise();
})();
