# Interactive dashboard

The static GitHub Pages dashboard lives under `docs/`. It keeps the existing
HTML, CSS, vanilla JavaScript, Leaflet, Papa Parse and Plotly stack. The page
visualises validated Python outputs and does not reproduce the GMPE or
vulnerability calculations in JavaScript.

## Primary model view

The primary view remains organised around three choices:

- earthquake;
- depth source: gWFM, ISC-EHB or gCMT; and
- map variable: Vs30, PGA or structural loss ratio.

The selected scenario shows maximum and arithmetic mean PGA and structural
loss ratio across the 311 receivers. Coordinates, rake, source availability,
minimum distances, the 30 km depth check, medians and non-zero loss counts are
under **More details**. The comparison charts preserve missing source depths
and use the tracked compact summary without changing its values.

### Vs30

The Vs30 layer uses `data/turkey_50km_land_grid_vs30.csv`. It preserves all 311
production values, direct/nearest-valid sampling status and fallback distance.

### PGA

The PGA layer reads `median_pga_g` from the selected event/depth JSON. All 311
values are strictly positive. Colour uses an event-specific continuous Viridis
scale in log(PGA), with minimum, geometric midpoint and maximum shown in g.

### Structural loss ratio

The structural-loss layer reads `structural_loss_ratio_mean` without changing
the stored ratio. Ratios are multiplied by 100 only for display. Exact zero is
grey and positive values use an event-specific linear scale.

Structural loss is conditional on the modelled PGA and the current GEM
residential structural function. It is not an insured, monetary, contents or
complete portfolio loss estimate.

## Separate exposure control

The **Exposure overlay** control is independent of the primary map variable:

- **None** is the default and loads no exposure data;
- **GEM province exposure** shows aggregate Adm1 building stock; and
- **Elazığ buildings** shows a descriptive OpenStreetMap footprint pilot.

Selecting or clearing an exposure never changes Vs30, PGA, structural loss,
the chosen event or the chosen depth source. Exposure failures clear only the
exposure layer; the receiver model remains usable.

### GEM province exposure

The GEM layer uses the open v2026.0.0 Türkiye summaries for Adm0, Adm1 and
taxonomy. The restricted/full 1 km model is not used. Province colour can show
total, residential, commercial or industrial `BUILDINGS`. The legend is
explicitly labelled **GEM exposure, Adm1 aggregate**.

Province popups show province, total/residential/commercial/industrial
buildings and residential occupants. Optional details show building
replacement cost and built-up area. Building replacement cost is not called
insured loss, and the polygons do not contain individual building locations.

The lower **Building stock** panel shows the five largest
`MACRO_TAXONOMY` groups and the five largest exact
`TAXONOMY`/`OCCUPANCY` records by `BUILDINGS`. Descriptions are copied from the
GEM Türkiye README. The complete 1,095-record settlement-aggregated taxonomy
summary remains available as JSON. No receiver structural loss is recalculated
for these building classes.

The pinned GEM source summaries are not numerically identical at the
single-building level: Adm0 totals 10,103,556 buildings, Adm1 totals 10,103,560
and the taxonomy summary totals 10,103,501. The dashboard preserves the
published source values and does not force an artificial reconciliation.

The Elazığ context card uses the exact province record:

```text
ID_1 = TR-23
NAME_1 = Elazığ
RES = 61,694 buildings
COM = 5,600 buildings
IND = 1,569 buildings
```

These are province totals and must not be described as Elazığ city counts.

### Elazığ OpenStreetMap pilot

The building pilot contains 1,583 closed OSM ways carrying a `building` tag.
It was extracted on 2026-09-03 with a one-time Overpass request using this
fixed central-Elazığ query bounding box:

```text
south = 38.66
west  = 39.18
north = 38.69
east  = 39.23
```

This box is not an official city or administrative boundary. The Overpass
bounding-box filter selects ways that intersect the query window, so a returned
building polygon may extend slightly beyond those coordinates. Each feature
retains its OSM way ID, original `building` tag, name and levels when supplied,
all source OSM tags, source, licence and retrieval date. Missing attributes are
not invented.

The live page never queries Overpass. It uses precomputed rendering levels:

- zoom 9 or lower: 5 coarse cluster/count symbols;
- zoom 10-13: 30 local cluster/count symbols; and
- zoom 14 or higher: individual footprint polygons.

Cluster counts reproduce the 1,583-feature total at both resolutions. The
881 KB footprint GeoJSON is fetched only after the Elazığ mode is selected and
the map reaches high zoom.

OSM footprints are descriptive geometry, not a complete structural inventory.
The required attribution is visible in both the map legend and information
panel: `© OpenStreetMap contributors`, ODbL 1.0. OSM tags have not been mapped
to GEM taxonomy. Every popup states `Vulnerability class: Not assigned`; no
building PGA or building structural loss is shown.

## Static exposure files and preprocessing

`prepare_gem_exposure_dashboard.py` reads the three open GEM summary CSVs plus
the GeoBoundaries input from ignored `data/external/` paths and writes:

```text
docs/data/exposure/gem_turkiye_adm1.json
docs/data/exposure/gem_turkiye_taxonomy.json
docs/data/exposure/gem_exposure_metadata.json
docs/data/exposure/turkiye_adm1.geojson
```

Run it from the repository root after placing the source files in the paths
documented in `docs/data/exposure/README.md`:

```powershell
python prepare_gem_exposure_dashboard.py --retrieved-on 2026-09-03
```

`prepare_elazig_osm_dashboard.py` downloads only when `--download` is supplied.
The raw Overpass response is stored under ignored `data/external/osm/`; the
derived browser files are:

```text
docs/data/exposure/elazig_buildings.geojson
docs/data/exposure/elazig_building_clusters.json
docs/data/exposure/elazig_osm_metadata.json
```

One-time download and later offline regeneration:

```powershell
python prepare_elazig_osm_dashboard.py --download --retrieved-on 2026-09-03
python prepare_elazig_osm_dashboard.py --retrieved-on 2026-09-03
```

The full provenance, pinned URLs, licences, retrieval date, join method and
limitations are in `docs/data/exposure/README.md` and the generated metadata.

## Receiver data export

Run the existing exporter after generating the validated complete model table:

```powershell
python build_dashboard_data.py
```

It selects and reformats existing values from the ignored complete table and
the tracked compact event/depth summary. It does not calculate PGA or
structural loss. It checks exactly 117 events, 321 valid depth scenarios, 311
receivers per scenario, finite values, scientific ranges and reproduction of
receiver-level means and maxima against the compact summary.

The 321 compact scenario files under `docs/data/events/` total approximately
10.2 MB and are loaded one at a time. The ignored 99,831-row complete table is
never downloaded by the browser.

## Loading, caching and errors

Validated receiver scenarios and exposure datasets have separate JavaScript
caches. On initial load the dashboard requests only the Turkey boundary,
production receiver table, compact event summary and dashboard manifest.

GEM JSON and Adm1 boundaries load only when GEM exposure is selected. The
Elazığ cluster summary, metadata and GEM context load only when the Elazığ
overlay is selected. Individual OSM polygons load only at zoom 14 or higher.

Malformed or unavailable exposure data show an exposure-specific error and do
not call the initial receiver-data failure path. Scenario errors likewise do
not leave stale receiver markers.

## Shareable state

The URL stores event, source, primary layer and exposure mode:

```text
?event=1421&source=waveform&layer=pga&exposure=none
```

Valid exposure values are `none`, `gem` and `elazig`. Missing or invalid values
fall back to `none`, so older Dashboard Version 2 URLs continue to work. Valid
primary layers remain `vs30`, `pga` and `loss`; their default remains PGA.

## Scientific separation

The dashboard deliberately keeps three concepts separate:

1. the validated 311-receiver PGA and structural-loss model;
2. aggregate GEM province exposure; and
3. mapped OSM footprints in the Elazığ pilot.

Current receiver structural loss uses only GEM v2026.0.0 function
`MUR+CLBRS/LWAL/CDN+ERN/H:1/RES`. GEM Adm1 exposure does not change that
function, and OSM footprints receive no vulnerability function. No
building-level structural-loss calculation has been validated.

## Local preview

From the repository root:

```powershell
cd docs
python -m http.server 8000
```

Then open `http://localhost:8000`. An internet connection is required for map
tiles and the pinned browser libraries. Repository JSON is served locally.

## GitHub Pages

The dashboard remains compatible with GitHub Pages from `main` and `/docs`:

```text
https://ibaadgeo.github.io/turkey-ground-motion-risk-model/
```

Versioned query strings on `dashboard.css` and `dashboard.js` prevent stale
interface assets after publication.
