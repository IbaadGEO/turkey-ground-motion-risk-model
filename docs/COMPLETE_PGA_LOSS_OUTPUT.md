# Complete PGA and Structural-Loss Output

## Purpose

This output gives one combined table containing PGA and the current GEM mean
structural loss ratio for every valid earthquake depth at every receiver
location.

The model has:

- 117 waveform depths;
- 110 ISC-EHB depths;
- 94 Global CMT depths;
- 321 valid earthquake-depth combinations in total; and
- 311 receiver locations.

This gives 99,831 rows in the complete table.

## Complete table

File:

`outputs_gwfm/complete_pga_structural_loss_table.csv`

Each row represents one event, one depth source and one receiver location.

The main columns are:

- `event_id`
- `origin_time`
- `magnitude`
- `depth_source`
- `source_depth_km`
- `location_id`
- `receiver_latitude`
- `receiver_longitude`
- `vs30_m_s`
- `repi_km`
- `rhypo_km`
- `median_pga_g`
- `structural_loss_ratio_mean`
- `source_within_30_km`
- `within_200_km`

`structural_loss_ratio_mean` is the current GEM structural vulnerability output.
It is the quantity being used here when discussing structural damage/loss
ratio. It is not a monetary or insured loss.

## Validation

The code checks that the complete table contains:

- 36,387 waveform rows;
- 34,210 ISC-EHB rows;
- 29,234 Global CMT rows;
- 99,831 rows in total;
- 321 unique event-depth combinations;
- exactly 311 receiver locations for every valid event-depth combination;
- no duplicate event-depth-location rows;
- no missing/non-finite PGA or loss values;
- PGA greater than zero; and
- structural loss ratio between zero and one.

## Compact summary

File:

`outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv`

This contains one row for each of the 321 valid earthquake-depth combinations.
It reports:

- receiver count;
- receivers within 200 km;
- minimum epicentral and hypocentral distance;
- median, mean and maximum PGA;
- median, mean and maximum structural loss ratio; and
- number of receiver locations with non-zero structural loss.

The full table is the main detailed output. The 321-row summary is intended for
quick inspection and comparison between the different depth sources.
