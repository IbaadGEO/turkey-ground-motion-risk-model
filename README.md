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

## Setup

The project has been run successfully on Windows with Python 3.13.7. A Python
3.12 Windows setup is also kept for reproducibility.

For Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py313.txt
```

For Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py312.txt
```

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

To run the separate 24 January 2020 Mww 6.7 Iris-event presentation example,
including its PGA-depth figure, loss-difference map and exact GEM
vulnerability curve, run:

```powershell
python iris_event_depth_analysis.py
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
- `pga_sensitivity_by_distance.png`: PGA sensitivity by distance; and
- `loss_sensitivity_by_distance.png`: structural-loss sensitivity by distance.

Presentation-specific Iris-event outputs are saved in
`outputs_gwfm/iris_event_analysis`:

- `iris_event_complete_results.csv`: all 3 depth scenarios across 311 receivers;
- `iris_event_depth_summary.csv`: compact summary for the 10, 12 and 14 km depths;
- `iris_event_gCMT_minus_analysed_map_data.csv`: receiver-level values behind the
  loss-difference map;
- `iris_event_pga_vs_depth.png`: PGA response to the three depth scenarios; and
- `iris_event_gCMT_minus_analysed_loss_difference_map.png`: gCMT minus analysed
  structural-loss difference.

The exact GEM structural vulnerability curve used by the model is also saved as:

- `outputs_gwfm/structural_vulnerability_curve.png`; and
- `outputs_gwfm/structural_vulnerability_curve_points.csv`.

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
- One residential building type is used at every location.
- Structural loss ratios are not insured or monetary loss estimates.
- The GEM vulnerability data are for non-commercial use under the included
  licence.
- `vs30_map.png` shows the 311 sampled receiver values. A full-raster
  TRVs30GeoM-versus-sampled-grid comparison figure is still outstanding.
