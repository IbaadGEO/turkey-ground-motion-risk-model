# Turkey ground-motion portfolio

This project uses the Akkar et al. (2014) hypocentral-distance ground-motion model in OpenQuake.

It calculates ground motion from a set of earthquakes at the 311 locations in the Turkey 50 km exposure grid. The existing nested loop pairs every earthquake with every exposure location.

The calculated intensity measures are:

- PGA;
- PGV;
- SA at 0.2 seconds; and
- SA at 1 second.

PGA is also passed through a provisional vulnerability curve to demonstrate the damage-ratio stage.

## Two runnable versions

### Five-event baseline

`akkar_turkey_portfolio.py` is the original working five-event demonstration. It remains unchanged and produces:

- 5 earthquakes;
- 311 exposure locations;
- 1,555 source-receiver pairs;
- 6,220 ground-motion rows; and
- 1,555 provisional damage rows.

Run it with:

```text
python akkar_turkey_portfolio.py
```

Its files are saved in `outputs`.

### 117-event gWFM run

`akkar_turkey_portfolio_gwfm.py` runs the selected gWFM v1.2 events. It has been tested with:

- 117 earthquakes;
- 311 exposure locations;
- 36,387 source-receiver pairs;
- 145,548 ground-motion rows; and
- 36,387 provisional damage rows.

Run it with:

```text
python akkar_turkey_portfolio_gwfm.py
```

Its files are saved in `outputs_gwfm`:

- `ground_motion_results.csv`;
- `provisional_damage_ratios.csv`;
- `exposure_and_earthquakes.png`; and
- `pga_map_1421.png`.

## gWFM inputs

`prepare_gwfm_catalogue.py` reads the gWFM text-table format and creates a normal CSV. It uses:

| gWFM field | Clean field |
|---|---|
| `id` | `event_id` |
| `yyyymmdd` and `hhmm` | `origin_time` |
| `wlon` | `longitude` |
| `wlat` | `latitude` |
| `wzc` | `depth_km` |
| `mag` | `magnitude` |
| `mty` | `magnitude_type` |
| waveform `rk` | `rake` |

The parser normalises unusual minus signs and converts rake angles to the `-180` to `180` degree range used by the GMPE.

The repository contains:

- `data/gwfm_v1_2_clean.csv`: all 2,312 cleaned gWFM records;
- `data/gwfm_117_event_selection.csv`: the 117 selected event IDs and matching source fields;
- `data/turkey_50km_land_grid.csv`: the 311 exposure locations; and
- `data/provisional_vulnerability_curve.csv`: the temporary PGA vulnerability curve.

The 117 selection was matched to gWFM using the supplied date, time, waveform longitude, waveform latitude and waveform depth. Every row matched exactly one gWFM event ID.

## Validation

Before the gWFM calculation starts, the code reports requested, matched, missing and duplicate IDs. It stops if an event is missing or duplicated.

It also stops if a selected earthquake has unusable coordinates, depth, magnitude or rake, or if its magnitude type is not `Mw`.

The vulnerability input must have increasing PGA values and damage ratios between 0 and 1.

Rows beyond 200 km are retained, but the terminal reports how many pairs are within and beyond 200 km.

## Separate depth example

`data/example_gwfm_5_depth_variation.csv` contains five real selected gWFM events with depths of 2, 8, 12, 21 and 162 km. It is a small depth-variation example and is separate from both the original five-event baseline and the full 117-event run.

## Current limitations

- Vs30 is fixed at 760 m/s for every location.
- The vulnerability curve is provisional and is not yet the agreed Turkish residential/no-contents model.
- Damage outputs are therefore labelled provisional.
- Pairs beyond 200 km are flagged but not automatically removed.
- The maps are longitude-latitude plots rather than full GIS maps.

See `PROJECT_WALKTHROUGH.md` for the complete code comparison, calculations, checks, limitations and live-demonstration instructions.
