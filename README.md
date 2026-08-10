# Turkey ground-motion portfolio

This project calculates earthquake ground motion at a 50 km grid of locations across Turkey.

The main calculation uses 117 selected earthquakes from the gWFM v1.2 catalogue and 311 exposure locations. For every earthquake-location pair, it calculates:

- PGA;
- PGV;
- spectral acceleration at 0.2 seconds; and
- spectral acceleration at 1.0 second.

PGA is also passed through a provisional vulnerability curve to produce a damage ratio between 0 and 1.

## Files

- `akkar_turkey_portfolio_gwfm.py`: runs the full 117-event calculation.
- `prepare_gwfm_catalogue.py`: reads and cleans the original gWFM text format.
- `akkar_turkey_portfolio.py`: five-event gCMT working example with a broader range of source depths.
- `data/gwfm_v1_2_clean.csv`: cleaned gWFM catalogue.
- `data/gwfm_117_event_selection.csv`: selected earthquake IDs.
- `data/turkey_50km_land_grid.csv`: 311 exposure locations.
- `data/provisional_vulnerability_curve.csv`: temporary vulnerability curve.

## Setup

The project was tested with Python 3.12. On Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py312.txt
```

## Run the full calculation

```powershell
python akkar_turkey_portfolio_gwfm.py
```

The tested run produces:

- 117 earthquakes;
- 311 exposure locations;
- 36,387 earthquake-location pairs;
- 145,548 ground-motion rows; and
- 36,387 provisional damage rows.

Results are saved in `outputs_gwfm`:

- `ground_motion_results.csv`;
- `provisional_damage_ratios.csv`;
- `exposure_and_earthquakes.png`; and
- `pga_map_1421.png`.

## Checks included

Before calculating ground motion, the program:

- reports requested, matched, missing and duplicate event IDs;
- checks that the full workflow contains 117 earthquakes and 311 exposure locations;
- checks latitude, longitude, depth, magnitude and rake;
- stops if a selected magnitude type is not `Mw`;
- reports how many selected earthquakes are deeper than the 30 km applicability range stated by Akkar et al. (2014);
- checks that vulnerability PGA values are ordered;
- checks that damage ratios stay between 0 and 1; and
- reports pairs within and beyond 200 km without deleting them.

## Current limitations

- Vs30 is fixed at 760 m/s at every location.
- The vulnerability curve is provisional.
- Damage results are therefore provisional.
- Some selected gWFM earthquakes are deeper than the 30 km focal-depth range stated for the Akkar et al. (2014) model. These events are retained and flagged pending a decision on their treatment.
- A decision is still needed on how to treat distances beyond 200 km.
