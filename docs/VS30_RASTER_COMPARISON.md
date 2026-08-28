# Vs30 full-raster comparison

## Purpose

Check whether the broad Vs30 pattern represented by the model's 311 receiver
values is consistent with the higher-resolution TRVs30GeoM raster, and quantify
the receiver-level differences between the two raster resolutions.

## Data

Production model input:

- `data/turkey_50km_land_grid_vs30.csv`
- 311 receiver locations
- values originally sampled from `TRVs30GeoM_9Arcsec.tif`
- 304 direct samples
- 7 nearest-valid samples

Validation raster:

- `data/external/TRVs30GeoM_3Arcsec.tif`
- CRS: `ESRI:102014`
- size: 22,557 x 13,090 cells
- projected cell size: approximately 75.18 m
- geographic bounds: approximately 24.83-46.77 E and 32.33-45.68 N
- the large TIFF is ignored by Git

## Method

`vs30_raster_comparison.py` samples the native 3-arcsecond raster at the same
311 receiver locations using the project's existing Vs30 validity range and
10 km nearest-valid fallback rule.

The numerical receiver comparison uses native raster samples. The full raster
is downsampled only for display in the presentation figure. This avoids
changing the data used for the numerical comparison while keeping the figure
manageable.

The script does not change the Vs30 values used by the production ground-motion
model.

## Checked results

Across all 311 receivers:

- 9-arcsecond production values: 304 direct, 7 nearest-valid
- 3-arcsecond validation values: 304 direct, 7 nearest-valid
- model Vs30 range: 174.03-619.15 m/s
- 3-arcsecond receiver range: 152.69-619.15 m/s
- median signed difference: 0.00 m/s
- median absolute difference: 0.52 m/s
- mean absolute difference: 5.02 m/s
- 95th percentile absolute difference: 20.85 m/s
- maximum absolute difference: 139.42 m/s
- Pearson correlation: 0.9883
- Spearman correlation: 0.9946
- 297 of 311 receivers differ by no more than 25 m/s
- 304 of 311 receivers differ by no more than 50 m/s

For the 304 direct-to-direct receiver comparisons:

- median absolute difference: 0.49 m/s
- mean absolute difference: 3.24 m/s
- 95th percentile absolute difference: 16.26 m/s
- Pearson correlation: 0.9956
- Spearman correlation: 0.9943

The largest resolution-dependent differences are concentrated at some of the
seven nearest-valid fallback locations.

## Interpretation

The 311-point receiver grid captures the broad spatial Vs30 pattern of the
higher-resolution raster well. The comparison does not show a broad
national-scale offset between the two resolutions. Most direct receiver
samples agree closely, while several coastal or fallback locations are more
sensitive to raster resolution because the nearest acceptable raster cell can
change.

This is a validation of spatial sampling and raster resolution. It is not a
replacement of the production Vs30 inputs.

## Outputs

Generated in `outputs_gwfm/vs30_raster_comparison`:

- `vs30_full_raster_vs_sampled_receivers.png`
- `vs30_3arcsec_minus_model_receivers.png`
- `vs30_3arcsec_receiver_comparison.csv`
- `vs30_raster_comparison_summary.csv`
