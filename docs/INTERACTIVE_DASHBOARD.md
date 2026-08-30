# Interactive dashboard

The repository includes a static interactive dashboard under `docs/`.

## Purpose

The dashboard provides a visual browser-based view of existing repository
outputs. It does not rerun the ground-motion model or vulnerability
calculations.

Version 1 includes:

- the Natural Earth Turkey boundary;
- the validated 311-location 50 km production receiver grid;
- receiver-level Vs30 values and sampling status;
- selected earthquake locations;
- filtering to the 90 earthquakes with gWFM, ISC-EHB and gCMT depths;
- a depth-source selector;
- selected-event metadata;
- source depth, event-level maximum PGA and event-level maximum structural loss;
- interactive depth, PGA and loss comparison charts.

## Data sources

The page reads the current `main` branch directly from:

- `data/turkey_boundary.geojson`
- `data/turkey_50km_land_grid_vs30.csv`
- `outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`

No duplicate scientific dataset is maintained inside `docs/`.

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

An internet connection is required for the OpenStreetMap tiles and the pinned
Leaflet, Papa Parse and Plotly browser libraries.

## GitHub Pages deployment

After the dashboard files are merged into `main`:

1. Open the repository on GitHub.
2. Go to **Settings** → **Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select branch **main**.
5. Select folder **/docs**.
6. Save.

The expected project URL is:

```text
https://ibaadgeo.github.io/turkey-ground-motion-risk-model/
```

## Scientific scope

PGA and structural-loss values in Version 1 are event-level summary values,
including maxima across the 311 production receivers. The general catalogue
view does not reconstruct receiver-level PGA or loss fields in the browser.

The dashboard intentionally visualises model outputs rather than duplicating
the validated Python calculations in JavaScript.
