# Turkey Ground-Motion Model

This project calculates earthquake ground motion across a 50 km grid of 311
locations in Turkey. Each location has its own Vs30 value.

It uses 117 selected earthquakes from the gWFM v1.2 catalogue. Where available,
each earthquake is calculated using three different depth sources:

- waveform depth;
- ISC-EHB depth; and
- Global CMT depth.

For each valid earthquake depth and location, the program calculates PGA, PGV,
SA(0.2 s) and SA(1.0 s). PGA is then used with a GEM residential structural
vulnerability curve to estimate a mean structural loss ratio between 0 and 1.

## Interactive visualisation

This GitHub repository is the primary project record for the scientific
methodology, source data, code, tests and derived outputs.

An optional browser-based dashboard is also available for visually exploring
the Turkey boundary, earthquake locations, the 50 km Vs30 receiver grid and
receiver-level PGA and structural-loss fields for each valid catalogue depth:

**[Open the interactive dashboard](https://ibaadgeo.github.io/turkey-ground-motion-risk-model/)**

Dashboard Version 2 loads only the selected event/depth receiver file, presents
maximum and mean PGA/loss values, and keeps Vs30, PGA and structural-loss map
legends specific to the active layer. An optional, separate exposure control
adds aggregate GEM province data or a small OpenStreetMap building-footprint
pilot for Elazığ. These overlays do not change the 311-receiver calculations,
and no OSM footprint has been assigned a GEM vulnerability class or
building-level loss. The dashboard remains a visual companion to the
repository and does not rerun the GMPE or vulnerability calculations in the
browser.

## Python setup

The project has been tested on Windows with Python 3.13.7. A Python 3.12
requirements file is also retained for reproducibility.

Create and activate a virtual environment, upgrade `pip`, then install the
requirements for the Python version being used:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py313.txt
```

For Python 3.12, create the environment with `py -3.12 -m venv .venv` and use
`requirements-windows-py312.txt` instead.

The common dependencies are listed in `requirements.txt`: NumPy, pandas,
Matplotlib, OpenQuake Engine, rasterio and `affine<3`.

## Project data, software and research sources

This section records the external datasets, project input files, software
implementations and research papers used directly by the workflow. Papers
reviewed only as background are not listed as model inputs.

### Earthquake catalogue and depth sources

**Global Waveform-Modelled Earthquake Catalogue (gWFM)**

- Production catalogue: `data/gwfm_v1_2_clean.csv`
- Selected-event file: `data/gwfm_117_event_selection.csv`
- Catalogue version: gWFM v1.2
- Source: COMET Global Waveform Catalogue
- Catalogue page: <https://comet.nerc.ac.uk/gwfm_catalogue/gWFM_catalogue.html>
- The project uses 117 selected earthquakes matched uniquely to gWFM.
- Waveform-modelled depth is the baseline depth in the main sensitivity
  analysis.

Reference:

Wimpenny, S. & Watson, C. S. (2021). *gWFM: A Global Catalog of
Moderate-Magnitude Earthquakes Studied Using Teleseismic Body Waves*.
Seismological Research Letters, 92(1), 212-226.
<https://doi.org/10.1785/0220200218>

**ISC-EHB depths**

The ISC-EHB values used by this project are the depth fields already carried
in the gWFM v1.2 input and retained in `data/gwfm_v1_2_clean.csv`; they are not
downloaded separately during a normal model run.

Key references:

- Engdahl, E. R., van der Hilst, R. & Buland, R. (1998). *Global teleseismic
  earthquake relocation with improved travel times and procedures for depth
  determination*. Bulletin of the Seismological Society of America, 88(3),
  722-743. <https://doi.org/10.1785/BSSA0880030722>
- Weston, J., Engdahl, E. R., Harris, J., Di Giacomo, D. & Storchak, D. A.
  (2018). *ISC-EHB: Reconstruction of a robust earthquake dataset*.
  Geophysical Journal International, 214(1), 474-484.
  <https://doi.org/10.1093/gji/ggy155>
- Engdahl, E. R., Di Giacomo, D., Sakarya, B., Gkarlaouni, C. G., Harris, J.
  & Storchak, D. A. (2020). *ISC-EHB 1964-2016, an improved data set for
  studies of Earth structure and global seismicity*. Earth and Space Science,
  7, e2019EA000897. <https://doi.org/10.1029/2019EA000897>

Official ISC-EHB information: <https://isc.ac.uk/isc-ehb/>

**Global CMT depths**

Global CMT values are also taken from the gWFM v1.2 input rather than queried
live during the calculation.

Reference:

Ekström, G., Nettles, M. & Dziewoński, A. M. (2012). *The global CMT project
2004-2010: Centroid-moment tensors for 13,017 earthquakes*. Physics of the
Earth and Planetary Interiors, 200-201, 1-9.
<https://doi.org/10.1016/j.pepi.2012.04.002>

Global CMT project: <https://www.globalcmt.org/>

### Ground-motion model

Ground motion is calculated with the hypocentral-distance form of the
Akkar-Sandikkaya-Bommer model, implemented in OpenQuake HazardLib as
`AkkarEtAlRhyp2014`.

The model receives magnitude, rake, Vs30 and hypocentral distance and is used
here to calculate PGA, PGV, SA(0.2 s) and SA(1.0 s).

Reference:

Akkar, S., Sandıkkaya, M. A. & Bommer, J. J. (2014). *Empirical ground-motion
models for point- and extended-source crustal earthquake scenarios in Europe
and the Middle East*. Bulletin of Earthquake Engineering, 12, 359-387.
<https://doi.org/10.1007/s10518-013-9461-4>

The repository flags source depths above 30 km and source-receiver distances
above 200 km because these lie outside the main stated applicability range of
the model.

Software implementation:

- OpenQuake Engine / HazardLib, GEM Foundation
- Project requirements use the OpenQuake Engine 3.26 dependency set
- Documentation: <https://docs.openquake.org/oq-engine/3.26/manual/>
- Source: <https://github.com/gem/oq-engine>

### Vs30 site-condition data

Vs30 is taken from the Türkiye-specific `TRVs30_GeoM` model.

Production input:

- local raster: `data/external/TRVs30GeoM_9Arcsec.tif`
- model input: `data/turkey_50km_land_grid_vs30.csv`
- 311 receiver locations
- 304 direct raster samples
- 7 nearest-valid samples within the 10 km fallback limit
- the large source raster is intentionally excluded from Git

Higher-resolution validation:

- local raster: `data/external/TRVs30GeoM_3Arcsec.tif`
- used by `vs30_raster_comparison.py`
- used to validate the spatial pattern and receiver-level values without
  replacing the production 9-arcsecond input

Dataset:

Okay, H. B. & Özacar, A. A. (2023). *TRVs30_GeoM - Türkiye Vs30 Model by
Geological Engineering Department of METU*. Zenodo.
<https://doi.org/10.5281/zenodo.10149864>

Research paper:

Okay, H. B. & Özacar, A. A. (2024). *A Novel VS30 Prediction Strategy Taking
Fluid Saturation into Account and a New VS30 Model of Türkiye*. Bulletin of
the Seismological Society of America, 114(2), 1048-1065.
<https://doi.org/10.1785/0120230032>

Derived exposure-grid files:

- `data/turkey_50km_land_grid.csv`: validated 311-location production grid
- `data/turkey_50km_land_grid_vs30.csv`: production grid with Vs30
- `data/turkey_20km_land_grid.csv` and `data/turkey_20km_land_grid_vs30.csv`:
  fine-grid case-study inputs
- `data/turkey_10km_land_grid.csv` and `data/turkey_10km_land_grid_vs30.csv`:
  higher-resolution fine-grid case-study inputs

The 10 km and 20 km grids are case-study/presentation grids and do not replace
the validated 50 km production grid.

### Structural vulnerability model

Structural loss ratios use the GEM Foundation Global Seismic Vulnerability
Model v2026.0.0.

Repository input:

- `data/gem_vulnerability_v2026/vulnerability_structural.xml`
- selected function: `MUR+CLBRS/LWAL/CDN+ERN/H:1/RES`
- selected intensity measure: PGA in g
- only structural loss is used
- contents, nonstructural and fatalities/occupants models are excluded
- licence: CC BY-NC-SA 4.0; the repository includes the licence text

Dataset:

Nafeh, A. M. B., Aljawhari, K. & Silva, V. (2026). *Global Seismic
Vulnerability Model (v2026.0.0)*. Zenodo.
<https://doi.org/10.5281/zenodo.20730225>

Structural vulnerability paper:

Aljawhari, K., Nafeh, A. M. B. & Silva, V. (2026). *A new global
vulnerability model for regional seismic risk assessments: Part 1 -
structural vulnerability*. Bulletin of Earthquake Engineering.
<https://doi.org/10.1007/s10518-026-02443-7>

GEM source repository:
<https://github.com/gem/global_vulnerability_model/tree/v2026.0.0>

### Dashboard exposure datasets

The optional dashboard exposure overlay uses only the open aggregate summaries
from the GEM Global Exposure Model v2026.0.0 Türkiye directory:

- `Exposure_Summary_Adm0.csv`;
- `Exposure_Summary_Adm1.csv`; and
- `Exposure_Summary_Taxonomy.csv`.

The pinned source is
<https://github.com/gem/global_exposure_model/tree/v2026.0.0/Europe/Turkiye>.
The GEM material is licensed CC BY-NC-SA 4.0 and uses GEM Building Taxonomy
v4.0. The restricted/full 1 km exposure model is not downloaded or used.

`prepare_gem_exposure_dashboard.py` validates the source schema, the 81 unique
Adm1 provinces, RES/COM/IND values, the `TR-23` Elazığ record and the one-to-one
boundary join. It exports static JSON and a simplified WGS84 GeoJSON under
`docs/data/exposure/`; the browser never fetches GEM GitHub at runtime.

The province geometry is the simplified geoBoundaries gbOpen Türkiye ADM1
dataset pinned to source commit `9469f09`. GEM's country README documents the
boundary source as GeoBoundaries under CC BY 4.0. The exact GeoBoundaries API
record used for the file identifies an OpenStreetMap-derived source and reports
CC BY-SA 2.0, so both provenance statements are retained in the generated
metadata rather than silently replacing one with the other.

`prepare_elazig_osm_dashboard.py` performs a documented one-time Overpass
extraction of closed, building-tagged OpenStreetMap ways intersecting a fixed central
Elazığ pilot box (`38.66, 39.18, 38.69, 39.23`). The box is not an official city
or administrative boundary. The resulting footprints and precomputed clusters
are static; the live dashboard does not query Overpass. OSM data are available
under ODbL 1.0 with attribution `© OpenStreetMap contributors`.

GEM Adm1 values are aggregate province exposure. OSM footprints are mapped
geometry rather than a complete structural inventory. OSM tags have not been
converted to GEM taxonomy, and no building-level structural-loss calculation
has been validated.

### Turkey boundary and mapping data

The Turkey outline used for grid generation and plotting is stored in
`data/turkey_boundary.geojson`.

Source:

- Natural Earth `ne_50m_admin_0_countries`
- version 5.1.2
- public domain
- source repository:
  <https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2>
- terms: <https://www.naturalearthdata.com/about/terms-of-use/>

The boundary is used for geographic clipping and visualisation rather than as
an earthquake or ground-motion input.

### 2020 Elazığ-Sivrice case-study inputs

The separate case-study workflow in `elazig_sivrice_depth_analysis.py` uses:

- origin time: 2020-01-24 17:55:13 UTC
- event code: `2020024175513`
- magnitude: Mww 6.7
- latitude: 38.3897
- longitude: 39.0883
- Wilber3 / USGS depth: 10 km
- Global CMT depth: 12 km
- analysed depth: 14 km
- representative rake: -12 degrees from the preferred USGS Mww moment tensor,
  nodal plane 2

USGS event page:
<https://earthquake.usgs.gov/earthquakes/eventpage/us60007ewc/executive>

The 14 km value is the separately analysed case-study depth used for the
placement comparison; it is not presented as a routine catalogue value.

### Derived repository files

The following are project-derived files rather than independent external
sources:

- cleaned and selected catalogue CSVs in `data/`;
- 10 km, 20 km and 50 km exposure-grid CSVs;
- sampled Vs30 CSVs;
- ground-motion and structural-loss result CSVs;
- depth-sensitivity summaries;
- catalogue-distribution summaries;
- Elazığ-Sivrice case-study CSVs; and
- all figures under `outputs_gwfm/`.

These files should be traced back to the source datasets and references above
rather than cited as independent external datasets.

## Run

Run the main model first:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

The main run uses `data/turkey_50km_land_grid_vs30.csv`, so the large Vs30
raster is not needed for a normal run.

The run also creates `outputs_gwfm/vs30_map.png` so the sampled values can be
checked visually.

To analyse how catalogue depth changes PGA and structural loss, run:

```powershell
python depth_sensitivity_analysis.py
```

The depth-sensitivity analysis uses the complete PGA/structural-loss table
from the main model. Its main comparison uses the 90 earthquakes that have
valid waveform, ISC-EHB and Global CMT depths.

To regenerate the presentation-ready catalogue-wide PGA and loss figures
without changing the numerical analysis, run:

```powershell
python presentation_figures.py
```

To run the separate 24 January 2020 Mww 6.7 Elazığ-Sivrice presentation example,
case-study earthquake selected by Iris from the waveform dataset,
including its PGA-depth figure, loss-difference map and exact GEM
vulnerability curve, run:

```powershell
python elazig_sivrice_depth_analysis.py
```

## Vs30 Data

Vs30 values come from the 9 arcsecond TRVs30GeoM model of Turkey:

https://doi.org/10.5281/zenodo.10149864

The grid contains 304 direct raster values. Seven coastal or edge locations
use the nearest value between 150 and 1200 m/s within 10 km. These rows and
their distances are marked in the CSV.

To recreate the Vs30 grid, place `TRVs30GeoM_9Arcsec.tif` in `data/external`
and run:

```powershell
python prepare_vs30_grid.py
```

### Full-raster Vs30 comparison

The production model continues to use the validated 311 receiver values sampled
from `TRVs30GeoM_9Arcsec.tif`. A separate validation workflow compares those
values with the higher-resolution `TRVs30GeoM_3Arcsec.tif` raster without
changing the production inputs.

Place `TRVs30GeoM_3Arcsec.tif` in `data/external` and run:

```powershell
python vs30_raster_comparison.py
```

The 1.2 GB source raster remains local and is ignored by Git. The comparison
uses the native 3-arcsecond raster to sample all 311 receiver locations and
only downsamples the raster for display.

Checked results:

- 311 receivers compared;
- current 9-arcsecond model values: 304 direct and 7 nearest-valid;
- 3-arcsecond samples: 304 direct and 7 nearest-valid;
- median signed difference: 0.0 m/s;
- median absolute difference: 0.52 m/s;
- mean absolute difference: 5.02 m/s;
- 95th percentile absolute difference: 20.85 m/s;
- Pearson correlation: 0.9883; and
- Spearman correlation: 0.9946.

For the 304 direct-to-direct receiver comparisons, the mean absolute
difference is 3.24 m/s and the Pearson correlation is 0.9956. The largest
differences are concentrated at some of the seven nearest-valid fallback
locations.

This comparison is a resolution and sampling check. It does not replace the
current 9-arcsecond Vs30 values used by the production model.

The tested main run produces:

- 321 valid earthquake-depth combinations;
- 99,831 earthquake-depth-location combinations;
- 399,324 ground-motion rows;
- 99,831 complete PGA/structural-loss rows; and
- 321 earthquake-depth summary rows.

## Outputs

Main-model results are saved in `outputs_gwfm`:

- `selected_event_depths.csv`: available and missing depths for each event;
- `ground_motion_results.csv`: calculated ground-motion values;
- `complete_pga_structural_loss_table.csv`: one row for every valid
  earthquake-depth-location scenario, with PGA and mean structural loss ratio;
- `complete_output/earthquake_depth_pga_loss_summary.csv`: one compact row for
  each of the 321 valid earthquake-depth combinations;
- `exposure_and_earthquakes.png`: exposure grid and earthquake map;
- `pga_map_1421.png`: example PGA map using waveform depth; and
- `vs30_map.png`: Vs30 values across the exposure grid.

Depth-sensitivity results are saved in
`outputs_gwfm/depth_sensitivity_analysis`:

- `depth_sensitivity_common_events_summary.csv`: fair comparison using the
  earthquakes with all three valid depth sources;
- `depth_sensitivity_all_available_summary.csv`: all available paired
  comparisons;
- `depth_sensitivity_depth_direction_summary.csv`: deeper, shallower and
  same-depth comparison;
- `depth_sensitivity_depth_direction_by_distance.csv`: depth direction split
  by epicentral-distance bin;
- `depth_sensitivity_common_event_ids.csv`: the common-event list;
- `depth_sensitivity_continuous_summary.csv`: 1 km plotting coordinates for
  the signed Gaussian-weighted mean and observed pair-to-pair spread;
- `depth_sensitivity_sign_balance.csv`: negative, unchanged and positive counts
  for 0-25 km and 0-200 km;
- `pga_sensitivity_by_distance.png`: signed PGA changes, raw paired values and
  a continuous distance trend; and
- `loss_sensitivity_by_distance.png`: signed structural-loss changes, raw
  paired values and a continuous distance trend;
- `catalogue_pga_loss_boxplots.png`: side-by-side event-level PGA and mean
  structural-loss distributions for the common three-catalogue earthquakes;
- `catalogue_boxplot_event_maxima.csv`: the balanced event-level values behind
  the boxplots; and
- `catalogue_boxplot_summary.csv`: quartiles, maxima and zero-loss event counts
  for each catalogue.

Run `python catalogue_distribution_plots.py` after the main analysis to
regenerate the catalogue-comparison figure and its two supporting CSV files.
Each plotted observation is one earthquake, represented by the maximum across
the 311 receivers, so the visual comparison does not treat the receiver rows
as independent earthquake samples. A short explanation of the sampling,
boxplot settings and axes is in
[`docs/CATALOGUE_BOXPLOT_WALKTHROUGH.md`](docs/CATALOGUE_BOXPLOT_WALKTHROUGH.md).

Presentation-specific Elazığ-Sivrice event outputs are saved in
`outputs_gwfm/elazig_sivrice_analysis`:

- `elazig_sivrice_complete_results.csv`: all 3 depth scenarios across 311 receivers;
- `elazig_sivrice_depth_summary.csv`: compact summary for the 10, 12 and 14 km depths;
- `elazig_sivrice_analysed_minus_gCMT_map_data.csv`: receiver-level values behind the
  loss-difference map;
- `elazig_sivrice_pga_vs_depth.png`: PGA response to the three depth scenarios; and
- `elazig_sivrice_analysed_minus_gCMT_loss_difference_map.png`: analysed 14 km minus
  gCMT 12 km structural-loss difference.

The exact GEM structural vulnerability curve used by the model is also saved as:

- `outputs_gwfm/structural_vulnerability_curve.png`; and
- `outputs_gwfm/structural_vulnerability_curve_points.csv`.

Full-raster Vs30 comparison outputs are saved in
`outputs_gwfm/vs30_raster_comparison`:

- `vs30_full_raster_vs_sampled_receivers.png`: full 3-arcsecond raster pattern
  compared with the 311 model receiver values using a common colour scale;
- `vs30_3arcsec_minus_model_receivers.png`: receiver-level 3-arcsecond minus
  current model Vs30 differences;
- `vs30_3arcsec_receiver_comparison.csv`: auditable receiver-level values and
  differences; and
- `vs30_raster_comparison_summary.csv`: compact comparison statistics.

## Complete PGA and structural-loss output

`complete_pga_structural_loss_table.csv` is the main combined output requested
for comparing all earthquakes at all available depths. It contains 99,831 rows:
one row for each valid event, depth source and receiver location. The key
columns are `event_id`, `depth_source`, `source_depth_km`, `location_id`,
`repi_km`, `rhypo_km`, `median_pga_g` and `structural_loss_ratio_mean`.

The code validates that the table contains 36,387 waveform rows, 34,210
ISC-EHB rows and 29,234 Global CMT rows, with exactly 311 receiver locations
for every valid earthquake-depth combination. PGA values must be positive and
structural loss ratios must be between zero and one.

The compact
`complete_output/earthquake_depth_pga_loss_summary.csv` contains 321 rows,
one per valid earthquake-depth combination, with median, mean and maximum PGA,
median, mean and maximum structural loss ratio, minimum distances and receiver
counts.

The 99,831-row complete CSV is a generated output and is ignored by Git. The
321-row summary is small enough to keep with the repository outputs.

## Current Limitations

- Some ISC-EHB and Global CMT depths are missing and are not used.
- Deep earthquakes and distances beyond 200 km are retained but flagged.
- One residential structural vulnerability function is applied at every model
  receiver; the receiver grid is not a building exposure inventory.
- Structural loss ratios are not insured or monetary loss estimates.
- GEM dashboard exposure is an aggregate province context layer, not individual
  building locations.
- The Elazığ OSM pilot is descriptive mapped geometry intersecting a fixed query
  box; it is not a complete city or province inventory.
- No OSM tag has been mapped to GEM taxonomy and no building-level PGA or
  structural loss has been calculated.
- The GEM vulnerability data are for non-commercial use under the included
  licence.
- `vs30_map.png` shows the 311 production receiver values. The separate
  full-raster validation compares them with the 3-arcsecond product but
  does not replace the production 9-arcsecond inputs.
