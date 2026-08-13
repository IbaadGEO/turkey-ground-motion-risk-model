# Turkey Ground-Motion Model

This project calculates earthquake ground motion across a 50 km grid of 311
locations in Turkey.

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

- Vs30 is fixed at 760 m/s for every location.
- Some ISC-EHB and Global CMT depths are missing and are not used.
- Deep earthquakes and distances beyond 200 km are retained but flagged.
- One residential building type is used at every location.
- Structural loss ratios are not insured or monetary loss estimates.
- The GEM vulnerability data are for non-commercial use under the included
  licence.
