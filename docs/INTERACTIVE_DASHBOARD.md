# Interactive dashboards

The GitHub Pages interface is now split into two deliberately separate scopes.
This separation prevents exploratory or newly updated data from being presented
as part of the fixed placement analysis.

## 1. Research dashboard

Entry point: `docs/index.html`

Purpose: visualise only the validated data and outputs produced for the current
placement project on earthquake-depth uncertainty.

The research dashboard contains:

- the 117 selected gWFM earthquakes;
- gWFM, ISC-EHB and gCMT source depths where available;
- the 90 common three-source events through the existing common-event filter;
- the 311 production Vs30 receiver locations;
- receiver-level Vs30, PGA and structural-loss values;
- the 321 valid event/depth scenarios;
- maximum, mean and median scenario metrics;
- depth-source comparison charts; and
- the current validated GEM residential structural vulnerability function used
  by the production calculation.

The browser continues to load compact per-scenario JSON files generated from the
validated Python outputs. It does not rerun the GMPE or vulnerability model in
JavaScript.

### Explicit research boundary

The research dashboard does **not** load or display:

- live/recent earthquake feeds;
- GEM province exposure summaries;
- OpenStreetMap building footprints;
- building clusters;
- unvalidated OSM-to-GEM taxonomy mappings; or
- building-level PGA or loss estimates.

The previously prepared exposure files and preprocessing scripts remain in the
repository as exploratory development material, but they are outside the active
research dashboard.

## 2. Expandable earthquake dashboard

Entry point: `docs/future.html`

Purpose: provide a separate place for newer earthquake catalogue data that can
change over time without changing the fixed placement results.

The page queries the USGS FDSN Event Web Service in GeoJSON format for a fixed
Türkiye-region bounding box. The default view requests the last 30 days and
magnitude 2.5+, with controls for 7/30/90 days and magnitude thresholds.
Refreshing the page or changing a control performs a new catalogue query.

The expandable dashboard currently displays only catalogue information:

- event origin time;
- magnitude;
- catalogue depth;
- coordinates;
- location description;
- USGS event identifier and review status; and
- a link to the source event record.

It deliberately does **not** calculate project-model PGA, sample project Vs30,
assign vulnerability, or estimate structural loss for these new events. Those
steps should only be added later through a validated extension of the Python
workflow.

## Technical stack

Research dashboard:

- HTML and CSS for structure and presentation;
- vanilla JavaScript for state and interaction;
- Leaflet for mapping;
- Plotly for comparison charts;
- Papa Parse for repository CSV inputs; and
- GitHub Pages for static hosting.

Expandable dashboard:

- HTML and CSS for structure and presentation;
- vanilla JavaScript for the updateable catalogue query;
- Leaflet for mapping;
- USGS FDSN Event Web Service for recent catalogue data; and
- GitHub Pages for static hosting.

The two pages are linked to each other but have different scientific scopes.
