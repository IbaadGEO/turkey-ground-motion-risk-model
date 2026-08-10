# Project notes

## What the project does

The original example calculated ground motion for a small number of earthquake and receiver inputs. The updated workflow reads earthquake and exposure files and repeats the calculation for every earthquake-location combination.

The existing Akkar et al. ground-motion calculation was kept. The main additions were catalogue loading, event selection, nested looping, validation, result files and maps.

## gWFM preparation

`prepare_gwfm_catalogue.py` reads the gWFM v1.2 text table and creates a simpler CSV with these columns:

| gWFM field | Output field |
|---|---|
| `id` | `event_id` |
| `yyyymmdd` and `hhmm` | `origin_time` |
| `wlon` | `longitude` |
| `wlat` | `latitude` |
| `wzc` | `depth_km` |
| `mag` | `magnitude` |
| `mty` | `magnitude_type` |
| waveform `rk` | `rake` |

Unusual minus signs are changed to normal minus signs before numerical conversion. Rake angles are converted to the range expected by the GMPE.

The supplied 117-event list was matched to the gWFM catalogue using date, time, longitude, latitude and waveform depth. All 117 rows matched one unique event ID.

## Calculation process

1. Load the cleaned gWFM catalogue.
2. Load the selected event IDs.
3. Check for missing or duplicate IDs.
4. Check the required earthquake values and magnitude types.
5. Load the 311 exposure locations.
6. Use an outer loop for earthquakes and an inner loop for locations.
7. Calculate hypocentral distance for every pair.
8. Calculate PGA, PGV, SA(0.2 s) and SA(1.0 s).
9. Pass PGA through the provisional vulnerability curve.
10. Save the CSV results and maps.

For 117 earthquakes and 311 locations:

```text
117 x 311 = 36,387 earthquake-location pairs
36,387 x 4 = 145,548 ground-motion rows
```

The tested run also produced 36,387 provisional damage rows.

## Distance check

The program marks whether each pair is within 200 km. The tested run reported:

```text
Pairs within 200 km: 2182
Pairs beyond 200 km: 34205
```

The rows beyond 200 km are currently retained.

## Maps

The script creates:

- a map of the 311 exposure locations and all 117 earthquakes; and
- a PGA map across the exposure grid for event `1421`.

## How to demonstrate it

Install the requirements and run:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

Then show:

1. the event validation printed in the terminal;
2. the earthquake, location and row counts;
3. `outputs_gwfm/ground_motion_results.csv`;
4. `outputs_gwfm/provisional_damage_ratios.csv`;
5. `outputs_gwfm/exposure_and_earthquakes.png`; and
6. `outputs_gwfm/pga_map_1421.png`.

## Work still outstanding

- Replace the provisional vulnerability curve when the final curve is agreed.
- Replace the fixed Vs30 value with location-specific values later.
- Confirm how selected earthquakes deeper than the 30 km Akkar et al. (2014) applicability range should be treated.
- Confirm how earthquake-location pairs beyond 200 km should be treated.
