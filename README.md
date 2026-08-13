# Turkey Ground-Motion Model

This project calculates earthquake ground motion across a 50 km grid of 311
locations in Turkey. Each location now has its own Vs30 value.

It uses 117 selected earthquakes from the gWFM v1.2 catalogue. Where available,
each earthquake is calculated using three different depth sources:

- waveform depth;
- ISC-EHB depth; and
- Global CMT depth.

For each valid earthquake depth and location, the program calculates PGA, PGV,
SA(0.2 s) and SA(1.0 s). PGA is then used with a GEM residential structural
vulnerability curve to estimate a mean structural loss ratio between 0 and 1.

## Setup

The project was tested with Python 3.12 on Windows.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py312.txt
```

## Run

```powershell
python akkar_turkey_portfolio_gwfm.py
```

The main run uses `data/turkey_50km_land_grid_vs30.csv`, so the large Vs30
raster is not needed for a normal run.

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

The tested run produces:

- 321 valid earthquake-depth combinations;
- 99,831 earthquake-depth-location combinations;
- 399,324 ground-motion rows; and
- 99,831 structural-loss-ratio rows.

## Outputs

Results are saved in `outputs_gwfm`:

- `selected_event_depths.csv`: available and missing depths for each event;
- `ground_motion_results.csv`: calculated ground-motion values;
- `structural_loss_ratios.csv`: estimated structural loss ratios;
- `exposure_and_earthquakes.png`: exposure grid and earthquake map; and
- `pga_map_1421.png`: example PGA map using waveform depth.

## Current Limitations

- Some ISC-EHB and Global CMT depths are missing and are not used.
- Deep earthquakes and distances beyond 200 km are retained but flagged.
- One residential building type is used at every location.
- Structural loss ratios are not insured or monetary loss estimates.
- The GEM vulnerability data are for non-commercial use under the included
  licence.
