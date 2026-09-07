# Earthquake Depth Uncertainty and Ground-Motion Sensitivity in Türkiye

## NERC Research Experience Placement, Summer 2026

## Project overview

This repository contains the scientific work completed during my NERC Research
Experience Placement in the Department of Earth Sciences at the University of
Cambridge.

The original placement project was titled:

**Investigating how the depth uncertainty propagates through probabilistic
seismic hazard models**

The project was motivated by the fact that automatically generated earthquake
catalogues can poorly constrain source depth, while waveform modelling can
provide more accurately constrained depths. Differences between these depth
estimates can exceed 10 km and may affect hazard calculations because source
depth changes source-to-receiver distance and therefore predicted ground
shaking.

The original brief focused on assessing how improved earthquake-depth estimates
influence hazard calculations in Türkiye. The work implemented in this
repository addresses that question through a reproducible ground-motion and
depth-sensitivity workflow using catalogue comparisons, Vs30 site conditions,
structural vulnerability calculations, case-study analysis and validation
tests.

The central question investigated here is:

> **How does uncertainty in earthquake depth affect predicted ground motion,
> and how does that effect propagate into a structural-loss estimate?**

The scripts, datasets, numerical outputs and figures are the main products of
the placement work.

---

## Main project workflow

The scientific workflow is:

1. collect and clean earthquake catalogue data;
2. identify earthquakes with alternative depth estimates;
3. compare gWFM, ISC-EHB and Global CMT depths;
4. create a national receiver grid across Türkiye;
5. assign a Vs30 value to each receiver;
6. calculate epicentral and hypocentral distances;
7. calculate ground motion for each event, depth source and receiver;
8. calculate structural-loss ratios from PGA;
9. compare results while changing only the assumed earthquake depth;
10. analyse how sensitivity changes with epicentral distance;
11. test the behaviour on the 2020 Elazığ-Sivrice earthquake;
12. validate the production Vs30 sampling against a higher-resolution raster;
13. generate numerical outputs and presentation figures.

---

## Production dataset

The final production workflow contains:

- **117 selected gWFM earthquakes**
- **110 earthquakes with ISC-EHB depths**
- **94 earthquakes with Global CMT depths**
- **90 earthquakes common to all three depth sources**
- **311 production receiver locations**
- **321 valid earthquake/depth scenarios**
- **99,831 earthquake-depth-receiver combinations**

The 90 common events form the balanced dataset used for the main
three-catalogue comparison.

The waveform-modelled gWFM depth is used as the reference depth in the paired
sensitivity analysis.

---

## Earthquake depth sources

### gWFM

The primary earthquake dataset is the Global Waveform-Modelled Earthquake
Catalogue, gWFM v1.2.

Production files:

- `data/gwfm_v1_2_clean.csv`
- `data/gwfm_117_event_selection.csv`

The waveform-modelled depths are used as the baseline for the main sensitivity
analysis.

Reference:

Wimpenny, S. & Watson, C. S. (2021). *gWFM: A Global Catalog of
Moderate-Magnitude Earthquakes Studied Using Teleseismic Body Waves*.
Seismological Research Letters, 92(1), 212-226.

<https://doi.org/10.1785/0220200218>

### ISC-EHB

ISC-EHB provides an alternative earthquake-depth estimate.

The ISC-EHB values used in this project are the depth fields carried in the
gWFM v1.2 input rather than depths downloaded through a live catalogue query.

Reference:

Weston, J., Engdahl, E. R., Harris, J., Di Giacomo, D. & Storchak, D. A.
(2018). *ISC-EHB: Reconstruction of a robust earthquake dataset*.
Geophysical Journal International, 214(1), 474-484.

<https://doi.org/10.1093/gji/ggy155>

### Global CMT

Global CMT provides the third depth source used in the comparison.

These values are also taken from the gWFM v1.2 input.

Reference:

Ekström, G., Nettles, M. & Dziewoński, A. M. (2012).
*The global CMT project 2004-2010: Centroid-moment tensors for 13,017
earthquakes*. Physics of the Earth and Planetary Interiors, 200-201, 1-9.

<https://doi.org/10.1016/j.pepi.2012.04.002>

---

## Catalogue depth comparison

The main catalogue comparison uses the **90 earthquakes for which all three
depth sources are available**.

### gWFM

- Q1: **9 km**
- median: **13 km**
- Q3: **33.25 km**
- IQR: **24.25 km**
- maximum: **162 km**

### ISC-EHB

- Q1: **10 km**
- median: **17 km**
- Q3: **39 km**
- IQR: **29 km**
- maximum: **162 km**

### Global CMT

- Q1: **15 km**
- median: **15 km**
- Q3: **32.75 km**
- IQR: **17.75 km**
- maximum: **151 km**

The comparison shows that the depth supplied to a ground-motion model can vary
substantially depending on the earthquake catalogue used.

---

## Receiver grid and Vs30

The production model evaluates ground motion at **311 receiver locations**
distributed across Türkiye on an approximately 50 km grid.

Production files:

- `data/turkey_50km_land_grid.csv`
- `data/turkey_50km_land_grid_vs30.csv`

Each receiver is assigned a Vs30 value from the Türkiye-specific
`TRVs30_GeoM` dataset.

The production input uses:

`TRVs30GeoM_9Arcsec.tif`

Of the 311 production receivers:

- **304** use a direct valid raster sample;
- **7** use the nearest valid Vs30 value within the permitted fallback distance.

The large source raster is kept locally and is not stored in Git.

Dataset:

Okay, H. B. & Özacar, A. A. (2023).
*TRVs30_GeoM - Türkiye Vs30 Model by Geological Engineering Department of
METU*.

<https://doi.org/10.5281/zenodo.10149864>

---

## How earthquake depth enters the model

For each earthquake and receiver, epicentral distance is combined with source
depth to calculate hypocentral distance:

```text
Rhyp = sqrt(Repi^2 + depth^2)
```

where:

- `Repi` is epicentral distance;
- `depth` is earthquake source depth;
- `Rhyp` is hypocentral distance.

In the current ground-motion implementation, earthquake depth affects the
prediction through `Rhyp`.

This explains why depth uncertainty has its strongest influence close to the
earthquake. At short epicentral distances, a change of several kilometres in
depth forms a relatively large part of the total source-to-receiver distance.

---

## Ground-motion model

Ground motion is calculated using the hypocentral-distance form of the
Akkar, Sandıkkaya and Bommer model implemented in OpenQuake HazardLib as:

`AkkarEtAlRhyp2014`

The model receives:

- earthquake magnitude;
- rake;
- Vs30;
- hypocentral distance.

The workflow calculates:

- PGA;
- PGV;
- SA(0.2 s);
- SA(1.0 s).

PGA is the main intensity measure used in the depth-sensitivity analysis.

Reference:

Akkar, S., Sandıkkaya, M. A. & Bommer, J. J. (2014).
*Empirical ground-motion models for point- and extended-source crustal
earthquake scenarios in Europe and the Middle East*.
Bulletin of Earthquake Engineering, 12, 359-387.

<https://doi.org/10.1007/s10518-013-9461-4>

Source depths above 30 km and source-receiver distances above 200 km are
retained in the calculations but flagged because they fall outside the main
stated applicability range of the model.

---

## Structural vulnerability calculation

PGA is also propagated through one structural vulnerability function from the
GEM Global Seismic Vulnerability Model v2026.0.0.

Selected function:

`MUR+CLBRS/LWAL/CDN+ERN/H:1/RES`

Input file:

`data/gem_vulnerability_v2026/vulnerability_structural.xml`

The output is a **mean structural-loss ratio between 0 and 1**.

This calculation is included to examine whether a change in PGA caused by a
different earthquake depth can propagate into a downstream impact metric.

The calculated value is:

- not insured loss;
- not monetary loss;
- not total economic loss;
- not a building-specific loss estimate.

Reference:

Nafeh, A. M. B., Aljawhari, K. & Silva, V. (2026).
*Global Seismic Vulnerability Model (v2026.0.0)*.

<https://doi.org/10.5281/zenodo.20730225>

---

## Depth-sensitivity analysis

For the main paired analysis, the earthquake and receiver remain unchanged
while the depth source is changed.

Signed PGA change is calculated as:

```text
100 × (PGA_comparison - PGA_gWFM) / PGA_gWFM
```

A negative value means the comparison depth produces lower PGA than the gWFM
depth.

A positive value means it produces higher PGA.

Structural-loss change is calculated as:

```text
loss_comparison - loss_gWFM
```

and plotted in percentage points.

---

## Distance-dependent sensitivity

The continuous sensitivity figures retain the underlying earthquake-receiver
pairs.

At each displayed epicentral distance, nearby observations are assigned
Gaussian weights based on their distance from that x-coordinate.

The bandwidth is **15 km**.

The shaded area is:

```text
weighted mean ± 1 weighted empirical standard deviation
```

This represents observed pair-to-pair variability.

It is not:

- a confidence interval;
- a formal uncertainty interval on the mean;
- sampled GMPE aleatory uncertainty.

---

## PGA sensitivity results

The strongest systematic depth effect occurs close to the earthquake.

### 0 to 25 km

Global CMT relative to gWFM:

- **85.7% lower PGA**
- **0% unchanged**
- **14.3% higher PGA**

ISC-EHB relative to gWFM:

- **64.3% lower PGA**
- **10.7% unchanged**
- **25.0% higher PGA**

### Gaussian-weighted mean PGA change

Global CMT relative to gWFM:

- 0 km: **-12.81%**
- 25 km: **-7.68%**
- 100 km: **-1.68%**
- 200 km: **-0.83%**

ISC-EHB relative to gWFM:

- 0 km: **-10.37%**
- 25 km: **-7.50%**
- 100 km: **-1.92%**
- 200 km: **-0.85%**

The systematic PGA influence decreases strongly with increasing epicentral
distance.

---

## Structural-loss sensitivity results

Structural loss responds less continuously than PGA because relatively small
PGA changes can map to the same or very similar part of the selected
vulnerability curve.

### 0 to 25 km

For both Global CMT and ISC-EHB comparisons:

- **21.4% lower structural loss**
- **71.4% unchanged**
- **7.1% higher structural loss**

### 0 to 200 km

Global CMT:

- **1465 of 1480 values unchanged**
- **98.99% unchanged**

ISC-EHB:

- **1466 of 1480 values unchanged**
- **99.05% unchanged**

The non-zero structural-loss differences are therefore highly concentrated
near the earthquake source.

---

## 2020 Elazığ-Sivrice case study

A separate event-specific analysis was completed for the:

**24 January 2020 Mww 6.7 Elazığ-Sivrice earthquake**

Parameters used include:

- origin time: `2020-01-24 17:55:13 UTC`
- latitude: `38.3897`
- longitude: `39.0883`
- Wilber3 / USGS depth: **10 km**
- Global CMT depth: **12 km**
- separately analysed depth: **14 km**

The 14 km value is the independently analysed case-study depth used for the
placement comparison and is not presented as a routine catalogue value.

---

## Fine-grid Elazığ tests

The production model uses the national 50 km receiver grid.

To test whether the structural-loss pattern was being hidden by coarse spatial
sampling, separate 10 km and 20 km grids were also evaluated around the
Elazığ-Sivrice earthquake.

### 10 km grid

Within 150 km:

- **705 receivers**
- **19 receivers with a non-zero structural-loss difference**
- **2.7% changed**
- **686 unchanged**

### 20 km grid

Within 150 km:

- **176 receivers**
- **6 receivers with a non-zero structural-loss difference**
- **3.4% changed**
- **170 unchanged**

These fine-grid tests show that the structural-loss response remains spatially
localised even when receiver density is increased.

---

## Vs30 resolution validation

The production model uses the 9-arcsecond TRVs30GeoM raster.

A separate validation workflow samples the native 3-arcsecond raster at the
same 311 receiver coordinates.

### All 311 receivers

- median signed difference: **0.00 m/s**
- median absolute difference: **0.52 m/s**
- mean absolute difference: **5.02 m/s**
- 95th percentile absolute difference: **20.85 m/s**
- maximum absolute difference: **139.42 m/s**
- Pearson correlation: **0.9883**
- Spearman correlation: **0.9946**
- **297 of 311** within 25 m/s
- **304 of 311** within 50 m/s

### Direct-to-direct samples only

For the 304 receivers with direct valid samples in both products:

- mean absolute difference: **3.24 m/s**
- 95th percentile absolute difference: **16.26 m/s**
- Pearson correlation: **0.9956**
- Spearman correlation: **0.9943**

The same seven receiver locations require nearest-valid sampling at both raster
resolutions.

This supports the interpretation that the fallback behaviour is associated
with the underlying raster coverage rather than being introduced by the
production raster resolution.

---

## Main scripts

### `akkar_turkey_portfolio_gwfm.py`

Runs the production ground-motion and structural-loss calculations.

### `depth_sensitivity_analysis.py`

Performs the paired depth-source sensitivity analysis and produces the signed
PGA and structural-loss results.

### `catalogue_distribution_plots.py`

Creates the catalogue-depth and catalogue-wide PGA/loss comparison figures.

### `presentation_figures.py`

Produces presentation-ready figures from the validated numerical outputs.

### `elazig_sivrice_depth_analysis.py`

Runs the event-specific Elazığ-Sivrice depth analysis and fine-grid
comparisons.

### `prepare_vs30_grid.py`

Samples the production TRVs30GeoM raster onto the 311-location receiver grid.

### `vs30_raster_comparison.py`

Compares the production Vs30 values with the higher-resolution 3-arcsecond
raster.

### `build_dashboard_data.py`

Converts already calculated scientific outputs into compact files for the
optional browser visualisation. It does not perform the GMPE or structural
vulnerability calculations.

---

## Main numerical outputs

### Complete PGA and structural-loss table

`outputs_gwfm/complete_pga_structural_loss_table.csv`

This contains **99,831 rows**.

Each row represents one:

```text
earthquake × depth source × receiver
```

Important fields include:

- `event_id`
- `depth_source`
- `source_depth_km`
- `location_id`
- `repi_km`
- `rhypo_km`
- `median_pga_g`
- `structural_loss_ratio_mean`

Source totals are:

- waveform: **36,387 rows**
- ISC-EHB: **34,210 rows**
- Global CMT: **29,234 rows**

### Earthquake-depth summary

`outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`

This contains **321 rows**, one for each valid earthquake/depth scenario.

---

## Depth-sensitivity outputs

Stored under:

`outputs_gwfm/depth_sensitivity_analysis/`

Important outputs include:

- `depth_sensitivity_common_events_summary.csv`
- `depth_sensitivity_all_available_summary.csv`
- `depth_sensitivity_depth_direction_summary.csv`
- `depth_sensitivity_depth_direction_by_distance.csv`
- `depth_sensitivity_common_event_ids.csv`
- `depth_sensitivity_continuous_summary.csv`
- `depth_sensitivity_sign_balance.csv`
- `pga_sensitivity_by_distance.png`
- `loss_sensitivity_by_distance.png`
- `catalogue_pga_loss_boxplots.png`
- `catalogue_boxplot_event_maxima.csv`
- `catalogue_boxplot_summary.csv`

---

## Elazığ-Sivrice outputs

Stored under:

`outputs_gwfm/elazig_sivrice_analysis/`

Outputs include:

- event results for the tested depth scenarios;
- depth-summary CSV files;
- fine-grid receiver results;
- PGA-versus-depth figures;
- structural-loss difference maps.

---

## Vs30 validation outputs

Stored under:

`outputs_gwfm/vs30_raster_comparison/`

Outputs include:

- `vs30_full_raster_vs_sampled_receivers.png`
- `vs30_3arcsec_minus_model_receivers.png`
- `vs30_3arcsec_receiver_comparison.csv`
- `vs30_raster_comparison_summary.csv`

---

## Reproducing the workflow

The project has been tested on Windows using Python 3.13.7.

Create the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py313.txt
```

Run the production model:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

Run the depth-sensitivity analysis:

```powershell
python depth_sensitivity_analysis.py
```

Regenerate the catalogue comparison:

```powershell
python catalogue_distribution_plots.py
```

Regenerate presentation figures:

```powershell
python presentation_figures.py
```

Run the Elazığ-Sivrice case study:

```powershell
python elazig_sivrice_depth_analysis.py
```

Run the Vs30 validation:

```powershell
python vs30_raster_comparison.py
```

Run the test suite:

```powershell
python -m unittest discover -s tests
```

---

## Additional interactive visualisation

As an **additional initiative alongside the main placement work**, I developed
a browser-based visualisation to make the validated scientific outputs easier
to inspect and compare interactively.

This was not part of the original placement brief and is not the main
scientific output of the project. The underlying datasets, Python scripts,
calculations, numerical results and figures remain the primary project record.

**[Open the interactive project results](https://ibaadgeo.github.io/turkey-ground-motion-risk-model/)**

The visualisation uses the existing validated placement outputs, including:

- selected earthquakes;
- alternative depth sources;
- the 311 production receivers;
- Vs30;
- PGA;
- structural-loss results.

It does not rerun the GMPE or vulnerability model in the browser.

A separate
**[experimental recent-earthquake explorer](https://ibaadgeo.github.io/turkey-ground-motion-risk-model/future.html)**
is retained as a small future-development exercise. New USGS events shown
there remain separate from the fixed placement dataset and are not currently
passed through the project PGA or structural-loss workflow.

Some GEM exposure and OpenStreetMap building files produced while exploring
possible future extensions are also retained in the repository for reference.
They are not part of the active placement analysis and no building-level PGA or
structural-loss claims are made from them.

---

## Current limitations

- Some ISC-EHB and Global CMT depths are unavailable.
- Deep earthquakes above 30 km are retained but flagged against the main GMPE
  applicability range.
- Source-receiver distances above 200 km are retained but flagged.
- The 50 km receiver grid is intended for national-scale sensitivity analysis,
  not detailed urban hazard mapping.
- One residential structural vulnerability function is applied at all
  receivers.
- The receiver grid is not a building inventory.
- Structural-loss ratios are not monetary or insured-loss estimates.
- Random GMPE aleatory uncertainty is not sampled in the current sensitivity
  analysis.
- The 3-arcsecond Vs30 raster is used only as a validation dataset and does not
  replace the production 9-arcsecond values.
- Exploratory GEM exposure and OpenStreetMap building data are kept separate
  from the validated scientific analysis.

---

## Repository purpose

This repository provides an auditable record of the placement workflow from
earthquake-depth data through ground-motion modelling, sensitivity analysis,
validation, figures and final numerical outputs.

The central scientific focus remains the original placement question:

**How much does uncertainty in earthquake depth matter for earthquake-hazard
estimates?**
