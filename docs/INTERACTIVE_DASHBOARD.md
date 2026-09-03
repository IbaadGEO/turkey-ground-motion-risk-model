# Interactive dashboard

The repository includes a static GitHub Pages dashboard under `docs/`. Version
2 keeps the existing HTML, CSS, vanilla JavaScript, Leaflet, Papa Parse and
Plotly stack. It visualises validated Python outputs and does not reproduce the
GMPE or vulnerability calculations in JavaScript.

## Version 2 overview

The primary view is organised around three choices:

- earthquake;
- depth source: gWFM, ISC-EHB or gCMT;
- map variable: Vs30, PGA or structural loss ratio.

The selected scenario shows four headline values from the tracked compact
summary:

- maximum PGA: highest modelled value among 311 receivers;
- mean PGA: arithmetic mean across all 311 receivers;
- maximum structural loss ratio: highest modelled value among 311 receivers;
- mean structural loss ratio: arithmetic mean across all 311 receivers.

Coordinates, rake, source availability, minimum distances, the 30 km depth
check, medians and non-zero loss counts remain available under **More details**.
The comparison area uses one depth chart, solid Maximum bars and orange diamond
Mean markers for PGA and structural loss, without filling missing catalogue
depths or changing the underlying values.

## Receiver map layers

### Vs30

The Vs30 layer uses `data/turkey_50km_land_grid_vs30.csv`. It preserves all 311
production receiver values, direct/nearest-valid sampling status and fallback
distance. Its legend uses the fixed site bins already used by the dashboard.

### PGA

The PGA layer reads `median_pga_g` from the selected event/depth JSON file. All
311 values are strictly positive. Colour uses an event-specific continuous
Viridis scale in log(PGA), with the minimum, geometric midpoint and maximum
shown explicitly in g. The logarithmic transform makes the broad positive PGA
range legible; the legend states the transform so it is not mistaken for a
linear scale.

### Structural loss ratio

The structural-loss layer reads `structural_loss_ratio_mean` without changing
the stored ratio. Ratios are multiplied by 100 only for display. Exact zero is
grey; positive values use an event-specific linear sequential scale from zero
to the selected scenario maximum. The legend and popups use percent units.

Structural loss ratio is conditional on the modelled PGA and current GEM
structural vulnerability function. It is not an insured, monetary, contents or
complete portfolio loss estimate.

## Dashboard data export

Run the exporter from the repository root after generating the validated
complete table:

```powershell
python build_dashboard_data.py
```

`build_dashboard_data.py` selects and reformats existing values from:

- `outputs_gwfm/complete_pga_structural_loss_table.csv`; and
- `outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`.

It does not calculate PGA or structural loss. Before writing output, it checks:

- exactly 117 unique events;
- 117 gWFM, 110 ISC-EHB and 94 Global CMT scenarios (321 total);
- exactly 311 unique receivers per scenario;
- a finite summary receiver count of 311 for every scenario;
- finite summary mean and maximum fields;
- finite coordinates and Vs30;
- strictly positive PGA;
- structural loss ratios between zero and one;
- exact correspondence between receiver and summary event/source keys;
- receiver-level mean and maximum PGA against the compact summary; and
- receiver-level mean and maximum loss ratio against the compact summary.

The browser files are written as:

```text
docs/data/dashboard_manifest.json
docs/data/events/<event_id>/<depth_source>.json
docs/data/vulnerability_functions.json
```

When `--output-directory` is supplied, this same tree is written entirely
beneath that directory. The production default remains `docs/data/`, and its
manifest paths remain browser-relative paths such as
`data/events/1421/waveform.json` so they resolve from `docs/index.html`.

Each scenario file stores the field names once and then 311 compact receiver
arrays. Event and source metadata are not repeated 311 times. The current
export contains 321 files totaling approximately 10.2 MB; individual scenario
files are approximately 31–33 KB. Only the selected scenario is requested.

Initial scientific data are approximately 194 KB before transfer compression:
the Turkey boundary, production receiver table, 321-row event summary and
dashboard manifest. The ignored 99,831-row complete table is never downloaded
by the browser.

## Loading, caching and errors

PGA and loss for one event/source share the same scenario JSON. The dashboard
stores successfully validated scenarios in a JavaScript `Map`, so switching
PGA to loss or returning to an earlier scenario does not fetch that file again.
A small status line reports loading, uncached timing, cache reuse or an error.

Before drawing a scenario, the browser checks the event/source identity, field
schema, receiver count, unique IDs, finite values and scientific ranges. A
missing source, missing file, network failure or malformed JSON clears the
previous thematic markers instead of leaving stale values. The source-independent
Vs30 layer remains available.

## Shareable state

The URL stores all three primary choices:

```text
?event=1421&source=waveform&layer=pga
```

Valid layer values are `vs30`, `pga` and `loss`. Invalid layer values fall back
to the documented default, PGA. A shared non-common event automatically turns
off the three-source-only filter so the requested event remains visible.

## Vulnerability and exposure scope

The open GEM Global Seismic Vulnerability Model v2026.0.0 structural XML is
stored in `data/gem_vulnerability_v2026/` under CC BY-NC-SA 4.0. The exporter
records the 521 source function IDs, distributions and IMTs in
`docs/data/vulnerability_functions.json`. The XML does not provide explicit
human-readable descriptions for those coded taxonomies, so none are invented.

Current production structural loss uses only:

```text
MUR+CLBRS/LWAL/CDN+ERN/H:1/RES
```

The dashboard does not let users choose another function because no validated
alternative receiver-level calculations exist.

No verified building-footprint or city-exposure dataset exists in the
repository. Version 2 therefore does not show fabricated building clusters or
assign open building tags to GEM taxonomies. The reproducible input contract
for a future licensed pilot is documented in `docs/data/exposure/README.md`.
Building/city risk remains a separate exposure-model extension, not completed
production science.

The preferred scientifically aligned source to investigate for that future
extension is the GEM Global Exposure Model v2026.0.0. It has not been
downloaded or integrated here. OpenStreetMap building footprints could provide
descriptive exposure geometry only unless a defensible building-to-GEM
taxonomy mapping is developed.

## Local preview

From the repository root:

```powershell
cd docs
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

An internet connection is required for OpenStreetMap tiles, the pinned browser
libraries and the published boundary/summary inputs. Scenario JSON files are
served locally from `docs/data/` during preview.

## GitHub Pages

The dashboard remains a static site compatible with deployment from `main` and
`/docs`:

```text
https://ibaadgeo.github.io/turkey-ground-motion-risk-model/
```

Versioned query strings on `dashboard.css` and `dashboard.js` prevent an older
interface from remaining in browser caches after publication.
