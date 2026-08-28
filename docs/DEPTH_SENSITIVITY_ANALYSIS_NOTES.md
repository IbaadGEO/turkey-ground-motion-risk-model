# Depth Sensitivity Analysis Notes

## Objective

Test how changing the catalogue depth for the same earthquake changes hypocentral distance, median PGA and mean structural loss ratio, and determine how that effect varies with epicentral distance.

## Method

- Use the existing `outputs_gwfm/complete_pga_structural_loss_table.csv` produced by the main workflow.
- Treat `waveform` depth as the baseline.
- Pair the same `event_id` and `location_id` with `isc_ehb` and `global_cmt` where those depths are available.
- Keep magnitude, rake, source location, receiver location and Vs30 unchanged.
- Calculate depth difference, hypocentral-distance difference, signed and absolute PGA change, and signed and absolute structural loss-ratio difference.
- Group results into 0-25, 25-50, 50-100, 100-200 and >200 km epicentral-distance bins.
- For the two presentation figures, retain every signed pair within 200 km and
  calculate a continuous 15 km Gaussian-weighted trend at 1 km intervals.

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
- `depth_sensitivity_continuous_summary.csv`
  - Continuous systematic signed tendency, observed standard deviation and
    weighted sign proportions used by the figures.
- `depth_sensitivity_sign_balance.csv`
  - Exact lower, unchanged and higher counts for 0-25 km and 0-200 km.
- `pga_sensitivity_by_distance.png`
  - Raw signed PGA changes, continuous signed mean and observed spread for the
    common-event set.
- `loss_sensitivity_by_distance.png`
  - Raw signed loss-ratio changes, continuous signed mean and observed spread
    for the common-event set.

The event-specific presentation example is now handled separately by
`elazig_sivrice_depth_analysis.py`. It uses the 24 January 2020 Mww 6.7
Elazığ-Sivrice earthquake, selected by Iris, and does not alter the validated
117-event catalogue-wide depth-sensitivity analysis.

## Important interpretation

The catalogue depths are observed/compiled input data, but PGA and structural loss ratios are modelled outputs. The loss result is conditional on the current GEM structural vulnerability function used by the project.

The continuous line is a systematic signed tendency: a line below zero means
the comparison catalogue generally lowers the modelled response relative to
gWFM. The shaded weighted standard deviation describes variation between the
event-receiver pairs. It must not be described as sampled random uncertainty;
the current workflow does not integrate the GMPE ground-motion uncertainty
into structural loss.

The binned CSV summary retains the >200 km category, but the continuous
presentation figures stop at the model's stated 200 km range. Earthquake
depths greater than 30 km are also retained and flagged by the main workflow.

## Checked result

The checked run used 90 earthquakes with all three valid depth sources, giving 55,980 common-event paired rows.

The strongest sensitivity is within 0-25 km. For gCMT, 85.7% of the signed PGA
changes are lower, 0.0% unchanged and 14.3% higher than gWFM. For ISC-EHB, the
corresponding proportions are 64.3%, 10.7% and 25.0%. For structural loss, both
catalogue comparisons contain 21.4% lower, 71.4% unchanged and 7.1% higher
near-field responses. The systematic signed tendency approaches zero with
increasing distance.
