(() => {
  "use strict";

  const RAW_BASE =
    "https://raw.githubusercontent.com/IbaadGEO/turkey-ground-motion-risk-model/main";
  const BOUNDARY_URL = `${RAW_BASE}/data/turkey_boundary.geojson`;
  const USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query";
  const REGION = Object.freeze({
    minlatitude: 35.0,
    maxlatitude: 43.0,
    minlongitude: 24.0,
    maxlongitude: 46.0,
  });
  const MAX_EVENTS = 500;

  const state = {
    map: null,
    boundaryLayer: null,
    eventLayer: null,
    events: [],
    markers: new Map(),
    requestToken: 0,
    selectedId: null,
  };

  const el = {
    window: document.getElementById("future-window"),
    minMag: document.getElementById("future-min-mag"),
    refresh: document.getElementById("future-refresh"),
    status: document.getElementById("future-status"),
    generated: document.getElementById("future-generated"),
    count: document.getElementById("future-count"),
    maxMag: document.getElementById("future-max-mag"),
    minDepth: document.getElementById("future-min-depth"),
    maxDepth: document.getElementById("future-max-depth"),
    tableBody: document.getElementById("future-table-body"),
    eventTitle: document.getElementById("future-event-title"),
    eventTime: document.getElementById("future-event-time"),
    eventMag: document.getElementById("future-event-mag"),
    eventDepth: document.getElementById("future-event-depth"),
    eventLat: document.getElementById("future-event-lat"),
    eventLon: document.getElementById("future-event-lon"),
    eventId: document.getElementById("future-event-id"),
    eventStatus: document.getElementById("future-event-status"),
    eventLink: document.getElementById("future-event-link"),
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[character]);
  }

  function formatNumber(value, digits = 1) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "–";
    return number.toLocaleString(undefined, { maximumFractionDigits: digits });
  }

  function formatUtc(timestamp) {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "Unknown time";
    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  }

  function setStatus(message, status = "ready") {
    el.status.textContent = message;
    el.status.className = `future-status ${status}`;
  }

  function initialiseMap() {
    state.map = L.map("future-map", {
      center: [39.0, 35.0],
      zoom: 5,
      minZoom: 4,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(state.map);

    state.boundaryLayer = L.featureGroup().addTo(state.map);
    state.eventLayer = L.featureGroup().addTo(state.map);
  }

  async function loadBoundary() {
    try {
      const response = await fetch(BOUNDARY_URL, { cache: "force-cache" });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const boundary = await response.json();
      const layer = L.geoJSON(boundary, {
        style: {
          color: "#334155",
          weight: 1.3,
          opacity: 0.75,
          fillOpacity: 0.02,
        },
      });
      state.boundaryLayer.addLayer(layer);
      state.map.fitBounds(layer.getBounds(), { padding: [18, 18] });
    } catch (error) {
      console.warn("Turkey boundary could not be loaded", error);
    }
  }

  function buildQueryUrl() {
    const days = Number(el.window.value);
    const minimumMagnitude = Number(el.minMag.value);
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    const params = new URLSearchParams({
      format: "geojson",
      eventtype: "earthquake",
      starttime: start.toISOString(),
      endtime: end.toISOString(),
      minlatitude: REGION.minlatitude.toString(),
      maxlatitude: REGION.maxlatitude.toString(),
      minlongitude: REGION.minlongitude.toString(),
      maxlongitude: REGION.maxlongitude.toString(),
      minmagnitude: minimumMagnitude.toString(),
      orderby: "time",
      limit: MAX_EVENTS.toString(),
    });
    return `${USGS_QUERY_URL}?${params.toString()}`;
  }

  function validateFeature(feature) {
    if (!feature || feature.type !== "Feature" || !feature.geometry) return null;
    if (feature.geometry.type !== "Point" || !Array.isArray(feature.geometry.coordinates)) return null;
    const [longitude, latitude, depth] = feature.geometry.coordinates.map(Number);
    const magnitude = Number(feature.properties && feature.properties.mag);
    const time = Number(feature.properties && feature.properties.time);
    if (![longitude, latitude, depth, magnitude, time].every(Number.isFinite)) return null;
    return {
      id: String(feature.id || feature.properties.code || `${time}-${longitude}-${latitude}`),
      longitude,
      latitude,
      depth,
      magnitude,
      time,
      place: String(feature.properties.place || "Location not supplied"),
      status: String(feature.properties.status || "unknown"),
      url: String(feature.properties.url || ""),
    };
  }

  function markerRadius(magnitude) {
    return Math.max(4, Math.min(18, 4 + Math.pow(Math.max(0, magnitude - 1.5), 1.45)));
  }

  function depthColour(depth) {
    if (depth < 10) return "#b91c1c";
    if (depth < 30) return "#ea580c";
    if (depth < 70) return "#ca8a04";
    return "#2563eb";
  }

  function selectEvent(eventId, pan = false) {
    const event = state.events.find((item) => item.id === eventId);
    if (!event) return;
    state.selectedId = event.id;

    el.eventTitle.textContent = event.place;
    el.eventTime.textContent = formatUtc(event.time);
    el.eventMag.textContent = `M ${formatNumber(event.magnitude, 1)}`;
    el.eventDepth.textContent = `${formatNumber(event.depth, 1)} km`;
    el.eventLat.textContent = `${formatNumber(event.latitude, 3)}°`;
    el.eventLon.textContent = `${formatNumber(event.longitude, 3)}°`;
    el.eventId.textContent = event.id;
    el.eventStatus.textContent = event.status;

    if (event.url) {
      el.eventLink.href = event.url;
      el.eventLink.hidden = false;
    } else {
      el.eventLink.hidden = true;
    }

    for (const [id, marker] of state.markers.entries()) {
      const selected = id === event.id;
      const markerEvent = state.events.find((item) => item.id === id);
      marker.setStyle({
        weight: selected ? 3 : 1,
        opacity: selected ? 1 : 0.85,
        fillOpacity: selected ? 0.92 : 0.68,
      });
      if (markerEvent) {
        marker.setRadius(markerRadius(markerEvent.magnitude) * (selected ? 1.18 : 1));
      }
    }

    if (pan) {
      state.map.flyTo([event.latitude, event.longitude], Math.max(state.map.getZoom(), 7), {
        duration: 0.6,
      });
    }
  }

  function renderMap() {
    state.eventLayer.clearLayers();
    state.markers.clear();

    for (const event of state.events) {
      const marker = L.circleMarker([event.latitude, event.longitude], {
        radius: markerRadius(event.magnitude),
        color: "#ffffff",
        weight: 1,
        fillColor: depthColour(event.depth),
        fillOpacity: 0.68,
      });
      marker.bindTooltip(
        `M ${formatNumber(event.magnitude, 1)} · ${escapeHtml(event.place)} · ${formatNumber(event.depth, 1)} km`,
        { sticky: true }
      );
      marker.on("click", () => selectEvent(event.id, false));
      marker.addTo(state.eventLayer);
      state.markers.set(event.id, marker);
    }
  }

  function renderSummary(metadata) {
    el.count.textContent = state.events.length.toLocaleString();
    if (!state.events.length) {
      el.maxMag.textContent = "–";
      el.minDepth.textContent = "–";
      el.maxDepth.textContent = "–";
    } else {
      const magnitudes = state.events.map((event) => event.magnitude);
      const depths = state.events.map((event) => event.depth);
      el.maxMag.textContent = `M ${formatNumber(Math.max(...magnitudes), 1)}`;
      el.minDepth.textContent = `${formatNumber(Math.min(...depths), 1)} km`;
      el.maxDepth.textContent = `${formatNumber(Math.max(...depths), 1)} km`;
    }

    const generated = Number(metadata && metadata.generated);
    el.generated.textContent = Number.isFinite(generated)
      ? `USGS response generated ${formatUtc(generated)}`
      : "USGS response loaded";
  }

  function renderTable() {
    if (!state.events.length) {
      el.tableBody.innerHTML = '<tr><td colspan="5">No events matched the current query.</td></tr>';
      return;
    }

    el.tableBody.innerHTML = state.events.slice(0, 100).map((event) => `
      <tr data-event-id="${escapeHtml(event.id)}" tabindex="0">
        <td>${escapeHtml(formatUtc(event.time))}</td>
        <td>M ${formatNumber(event.magnitude, 1)}</td>
        <td>${formatNumber(event.depth, 1)}</td>
        <td>${escapeHtml(event.place)}</td>
        <td><code>${escapeHtml(event.id)}</code></td>
      </tr>
    `).join("");

    for (const row of el.tableBody.querySelectorAll("tr[data-event-id]")) {
      const activate = () => selectEvent(row.dataset.eventId, true);
      row.addEventListener("click", activate);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") activate();
      });
    }
  }

  async function refreshEvents() {
    const requestToken = ++state.requestToken;
    el.refresh.disabled = true;
    setStatus("Loading recent USGS earthquakes…", "loading");

    try {
      const response = await fetch(buildQueryUrl(), { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      const payload = await response.json();
      if (requestToken !== state.requestToken) return;
      if (!payload || payload.type !== "FeatureCollection" || !Array.isArray(payload.features)) {
        throw new Error("USGS response was not a GeoJSON FeatureCollection");
      }

      state.events = payload.features
        .map(validateFeature)
        .filter(Boolean)
        .sort((a, b) => b.time - a.time);

      renderMap();
      renderSummary(payload.metadata || {});
      renderTable();

      if (state.events.length) {
        selectEvent(state.events[0].id, false);
      } else {
        state.selectedId = null;
        el.eventTitle.textContent = "No matching earthquakes";
        el.eventTime.textContent = "Change the time window or magnitude threshold.";
        el.eventLink.hidden = true;
      }

      const truncated = payload.metadata && Number(payload.metadata.count) >= MAX_EVENTS;
      setStatus(
        `${state.events.length.toLocaleString()} recent events loaded from USGS.${truncated ? " Query reached the 500-event display limit." : ""}`
      );
    } catch (error) {
      console.error("Recent earthquake query failed", error);
      if (requestToken === state.requestToken) {
        setStatus(
          "Recent earthquake data could not be loaded. The fixed research dashboard is unaffected.",
          "error"
        );
      }
    } finally {
      if (requestToken === state.requestToken) el.refresh.disabled = false;
    }
  }

  function bindControls() {
    el.refresh.addEventListener("click", refreshEvents);
    el.window.addEventListener("change", refreshEvents);
    el.minMag.addEventListener("change", refreshEvents);
  }

  initialiseMap();
  bindControls();
  void loadBoundary();
  void refreshEvents();
})();
