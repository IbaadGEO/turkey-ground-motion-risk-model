# Project notes

## What the project does

The production workflow reads the selected gWFM earthquake catalogue and
Turkey exposure grid, then repeats the Akkar et al. ground-motion calculation
for every valid earthquake-depth-location combination. It includes catalogue
loading, event selection, nested looping, validation, result files and maps.

## gWFM preparation

`prepare_gwfm_catalogue.py` reads the gWFM v1.2 text table and creates a simpler CSV with these columns:

| gWFM field | Output field |
|---|---|
| `id` | `event_id` |
| `yyyymmdd` and `hhmm` | `origin_time` |
| `wlon` | `longitude` |
| `wlat` | `latitude` |
| `wzc` | `waveform_depth_km` |
| `izc` | `isc_ehb_depth_km` |
| `czc` | `global_cmt_depth_km` |
| `mag` | `magnitude` |
| `mty` | `magnitude_type` |
| waveform `rk` | `rake` |

Unusual minus signs are changed to normal minus signs before numerical conversion. Rake angles are converted to the range expected by the GMPE.

The supplied 117-event list was matched to the gWFM catalogue using date,
time, longitude, latitude and waveform depth. All 117 rows matched one unique
event ID. Its supplied CMT depths match all 88 overlapping embedded gWFM CMT
depths and provide six additional positive CMT depths.

The final depth table contains three rows per event: waveform, ISC-EHB and
Global CMT. A depth is only used when it is positive and finite. The `-10` CMT
sentinel, six missing ISC-EHB values and one zero ISC-EHB value are recorded
with statuses rather than passed into the GMPE.

## Calculation process

1. Load the cleaned gWFM catalogue.
2. Load the selected event IDs.
3. Check for missing or duplicate IDs.
4. Check the required earthquake values and magnitude types.
5. Build the waveform, ISC-EHB and Global CMT depth rows.
6. Load the 311 exposure locations.
7. Loop through earthquakes, valid depths and locations.
8. Calculate hypocentral distance for every scenario.
9. Calculate PGA, PGV, SA(0.2 s) and SA(1.0 s).
10. Pass median PGA through the selected GEM v2026 structural vulnerability
   function.
11. Build a validated complete PGA/structural-loss table with one row for every
   valid earthquake-depth-location combination.
12. Build a compact one-row-per-earthquake-depth summary.
13. Save the depth table, calculation results and maps.

The 117 events contain 321 usable depth scenarios:

```text
117 waveform + 110 ISC-EHB + 94 Global CMT = 321 valid depths
321 x 311 = 99,831 earthquake-depth-location pairs
99,831 x 4 = 399,324 ground-motion rows
```

The tested run also produces a 99,831-row complete PGA/structural-loss
table and a 321-row earthquake-depth summary.

## Structural vulnerability selection

The project uses function `MUR+CLBRS/LWAL/CDN+ERN/H:1/RES` from the GEM Global
Vulnerability Model `v2026.0.0`. It represents a one-storey residential,
unreinforced solid-clay-brick masonry building with load-bearing walls, no
design code and no earthquake-resistant design. The function uses PGA in g,
so the existing ground-motion measures do not need to change.

Only `vulnerability_structural.xml` is loaded. Contents, nonstructural and
fatalities/occupants models are excluded. The output is the curve's mean
structural loss ratio conditional on median PGA. It is not a complete insured
loss or portfolio loss because the current workflow does not include contents,
asset values, building counts, a location-specific taxonomy mixture, or
integration over ground-motion uncertainty.

## Distance check

The program marks whether each pair is within 200 km. The tested run reported:

```text
Pairs within 200 km: 2182
Pairs beyond 200 km: 34205
```

Those figures are the waveform-depth baseline. Across all three valid depth
sources, 5,656 pairs are within 200 km and 94,175 are beyond 200 km. The rows
beyond 200 km are currently retained.

## Maps

The script creates:

- a map of the 311 exposure locations and all 117 earthquakes; and
- a waveform-depth PGA map across the exposure grid for event `1421`.

The PGA map shows exact zero values in grey. Positive values use the
perceptually uniform `viridis` colour map on a logarithmic scale so that low
non-zero ground motions remain distinguishable. Both map types include a black
Turkey outline derived
from Natural Earth's public-domain `ne_50m_admin_0_countries` dataset,
version 5.1.2.

## Vs30 full-raster validation

The production model uses 311 receiver Vs30 values sampled from the
9-arcsecond TRVs30GeoM product. A separate validation script,
`vs30_raster_comparison.py`, compares those values with the higher-resolution
3-arcsecond TRVs30GeoM raster while leaving the production model unchanged.

The 3-arcsecond source raster is read directly from
`data/external/TRVs30GeoM_3Arcsec.tif`. Native raster cells are sampled at all
311 receiver locations. The raster is downsampled only for plotting so that
the 1.2 GB source does not need to be loaded into a presentation figure at
native display resolution.

The checked comparison contains 311 receivers. Both products give 304 direct
samples and 7 nearest-valid samples. Across all receivers, the median signed
3-arcsecond minus model difference is 0.0 m/s, the median absolute difference
is 0.52 m/s, the mean absolute difference is 5.02 m/s and the 95th percentile
absolute difference is 20.85 m/s. Pearson and Spearman correlations are 0.9883
and 0.9946 respectively.

For the 304 direct-to-direct comparisons, the mean absolute difference is
3.24 m/s and Pearson correlation is 0.9956. The largest differences are
concentrated at some of the seven fallback locations. The comparison therefore
supports the conclusion that the 311-point model grid preserves the broad
spatial Vs30 pattern, while also identifying the fallback locations as the
main source of resolution-dependent differences.

Generated outputs are stored in
`outputs_gwfm/vs30_raster_comparison`.

## How to demonstrate it

Install the requirements and run:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

Then show:

1. the event validation printed in the terminal;
2. the earthquake, location and row counts;
3. `outputs_gwfm/ground_motion_results.csv`;
4. `outputs_gwfm/complete_pga_structural_loss_table.csv`;
5. `outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`;
6. `outputs_gwfm/selected_event_depths.csv`;
7. `outputs_gwfm/exposure_and_earthquakes.png`; and
8. `outputs_gwfm/pga_map_1421.png`.

## Work still outstanding

- Add a location-specific building inventory or taxonomy mixture if the model
  is extended beyond the current representative structural scenario.
- Confirm whether the seven nearest-cell Vs30 replacements are acceptable.
- Confirm how selected earthquakes deeper than the 30 km Akkar et al. (2014) applicability range should be treated.
- Confirm how earthquake-location pairs beyond 200 km should be treated.
