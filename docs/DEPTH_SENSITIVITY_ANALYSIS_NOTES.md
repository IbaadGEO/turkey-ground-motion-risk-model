# Depth Sensitivity Analysis Notes

## Objective

Test how changing the catalogue depth for the same earthquake changes hypocentral distance, median PGA and mean structural loss ratio, and determine how that effect varies with epicentral distance.

## Method

- Use the existing `outputs_gwfm/structural_loss_ratios.csv` produced by the main workflow.
- Treat `waveform` depth as the baseline.
- Pair the same `event_id` and `location_id` with `isc_ehb` and `global_cmt` where those depths are available.
- Keep magnitude, rake, source location, receiver location and Vs30 unchanged.
- Calculate depth difference, hypocentral-distance difference, signed and absolute PGA change, and signed and absolute structural loss-ratio difference.
- Group results into 0-25, 25-50, 50-100, 100-200 and >200 km epicentral-distance bins.

## Fair catalogue comparison

The number of earthquakes with an ISC-EHB depth is different from the number with a Global CMT depth. The main figures therefore use only earthquakes that contain all three valid depth sources: waveform, ISC-EHB and Global CMT.

The script also saves an all-available summary separately.

## Loss metrics

The median loss difference can be zero when most receiver locations are below the first vulnerability-curve intensity level. The analysis therefore also reports:

- mean absolute structural loss-ratio difference;
- 95th percentile absolute structural loss-ratio difference;
- maximum absolute structural loss-ratio difference;
- percentage of pairs with a loss change above a small numerical tolerance;
- percentage of pairs with an absolute loss-ratio change of at least `1e-6`.

The `1e-6` threshold equals 0.0001 percentage points of structural loss and is included only as a practical reporting threshold.

## Depth direction

The common-event results are also grouped into deeper, shallower and same-depth cases so the direction of the PGA and loss response can be checked.

## Files generated

- `depth_sensitivity_all_available_summary.csv`
  - Uses every available waveform/alternative pair.
- `depth_sensitivity_common_events_summary.csv`
  - Same common-event summary with an explicit name.
- `depth_sensitivity_common_event_ids.csv`
  - Earthquakes with all three valid depth sources.
- `depth_sensitivity_depth_direction_summary.csv`
  - Overall deeper/shallower/same-depth comparison.
- `depth_sensitivity_depth_direction_by_distance.csv`
  - Deeper/shallower/same-depth results split by epicentral-distance bin.
- `pga_sensitivity_by_distance.png`
  - Median absolute PGA change for the common-event set.
- `loss_sensitivity_by_distance.png`
  - Mean and 95th percentile absolute loss-ratio difference for the common-event set.
- `event_1421_global_cmt_loss_difference_map.png`
  - Near-field map of the geographic loss-ratio difference for event 1421,
    using receivers within 150 km.

## Important interpretation

The catalogue depths are observed/compiled input data, but PGA and structural loss ratios are modelled outputs. The loss result is conditional on the current GEM structural vulnerability function used by the project.

The >200 km bin is retained to show the trend, but the project already flags source-receiver pairs beyond 200 km. Earthquake depths greater than 30 km are also retained and flagged by the main workflow.

## Checked result

The checked run used 90 earthquakes with all three valid depth sources, giving 55,980 common-event paired rows.

The strongest sensitivity is within 0-25 km. In that bin, the median absolute PGA change is 26.3% for Global CMT versus waveform and 14.4% for ISC-EHB versus waveform. Practical structural-loss changes occur in 25.0% and 21.4% of those near-field pairs respectively, and become negligible with increasing distance.
