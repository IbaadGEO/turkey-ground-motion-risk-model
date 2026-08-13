# Turkey ground-motion portfolio

This project calculates earthquake ground motion at a 50 km grid of locations across Turkey.

The main calculation uses 117 selected earthquakes from the gWFM v1.2
catalogue and 311 exposure locations. Each earthquake can use waveform,
ISC-EHB and Global CMT depth estimates. For every valid
earthquake-depth-location scenario, it calculates:

- PGA;
- PGV;
- spectral acceleration at 0.2 seconds; and
- spectral acceleration at 1.0 second.

PGA is also passed through the exact
`CR/LFINF/CDL+ERL/H:2/RES` function from the GEM Global Vulnerability Model
`v2026.0.0`. This produces a mean structural loss ratio between 0 and 1,
conditional on median PGA.

## Files

- `akkar_turkey_portfolio_gwfm.py`: runs the full 117-event calculation.
- `prepare_gwfm_catalogue.py`: reads and cleans the original gWFM text format.
- `map_plotting.py`: Turkey-border and PGA-point plotting functions.
- `vulnerability.py`: validates and applies one OpenQuake NRML structural
  vulnerability function.
- `data/gwfm_v1_2_clean.csv`: cleaned gWFM catalogue with waveform, ISC-EHB
  and embedded Global CMT depths.
- `data/gwfm_117_event_selection.csv`: selected earthquake IDs and supplied
  Global CMT comparison depths.
- `data/turkey_50km_land_grid.csv`: 311 exposure locations.
- `data/turkey_boundary.geojson`: Turkey national outline used by every map.
- `data/gem_vulnerability_v2026/vulnerability_structural.xml`: pinned GEM
  structural model used by the production workflow.

The repository contains the selected production gWFM inputs and automated
validation tests. No demonstration earthquake catalogue, demonstration output
or temporary vulnerability data is retained.

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
- 321 valid event-depth scenarios;
- 311 exposure locations;
- 99,831 earthquake-depth-location pairs;
- 399,324 ground-motion rows; and
- 99,831 mean structural-loss-ratio rows.

Results are saved in `outputs_gwfm`:

- `ground_motion_results.csv`;
- `structural_loss_ratios.csv`;
- `selected_event_depths.csv`;
- `exposure_and_earthquakes.png`; and
- `pga_map_1421.png`.

The PGA map shows exact zero values in grey. Positive values use the
perceptually uniform `viridis` colour map on a logarithmic scale so that low
non-zero ground motions remain distinguishable. Every map includes a black
Turkey outline derived from
Natural Earth's public-domain `ne_50m_admin_0_countries` dataset, version 5.1.2.

## Checks included

Before calculating ground motion, the program:

- reports requested, matched, missing and duplicate event IDs;
- checks that the full workflow contains 117 earthquakes and 311 exposure locations;
- checks latitude, longitude, waveform depth, magnitude and rake;
- records missing or invalid ISC-EHB and Global CMT depths without guessing;
- checks overlapping supplied and embedded Global CMT depths agree;
- stops if a selected magnitude type is not `Mw`;
- reports how many selected earthquakes are deeper than the 30 km applicability range stated by Akkar et al. (2014);
- requires the exact selected vulnerability function;
- rejects any model not labelled as structural building vulnerability;
- checks the curve's PGA values and mean structural loss ratios; and
- reports pairs within and beyond 200 km without deleting them.

## Current limitations

- Vs30 is fixed at 760 m/s at every location.
- Depth coverage is incomplete: 110 events have valid ISC-EHB depths and 94
  have valid Global CMT depths. Missing and invalid depths are retained in the
  depth table but excluded from the GMPE calculation.
- One representative residential building taxonomy is currently applied to
  every location; a location-specific building inventory is not yet included.
- Contents, nonstructural and fatalities/occupants vulnerability models are
  deliberately excluded.
- The output is conditional on median PGA and does not integrate ground-motion
  uncertainty, building counts or replacement values. It is therefore not a
  complete portfolio loss or insured-loss estimate.
- The GEM vulnerability data are licensed CC BY-NC-SA 4.0 and are restricted
  to non-commercial use under that licence.
- Some selected gWFM earthquakes are deeper than the 30 km focal-depth range stated for the Akkar et al. (2014) model. These events are retained and flagged pending a decision on their treatment.
- A decision is still needed on how to treat distances beyond 200 km.
