# Presentation figure updates

This work keeps the validated 117-event production catalogue unchanged and adds a separate Iris-event presentation analysis.

## Updated catalogue-wide figures

`presentation_figures.py` reads the existing numerical depth-sensitivity summary and regenerates:

- `pga_sensitivity_by_distance.png`
- `loss_sensitivity_by_distance.png`

Colour meaning is fixed across both figures:

- gCMT = blue
- ISC-EHB = orange

The loss figure uses solid lines for means and dashed lines for 95th percentiles. Both figures show sample sizes by distance bin.

## Iris-event example

`iris_event_depth_analysis.py` uses:

- 2020-01-24 17:55:13
- event code `2020024175513`
- Mww 6.7
- latitude 38.3897
- longitude 39.0883
- Wilber3 / USGS = 10 km
- gCMT = 12 km
- analysed depth = 14 km

It reuses the same Akkar Rhyp GMPE, 311 receiver locations, local Vs30 values and GEM structural vulnerability function as the main project.

Outputs:

- `iris_event_pga_vs_depth.png`
- `iris_event_gCMT_minus_analysed_loss_difference_map.png`
- `iris_event_complete_results.csv`
- `iris_event_depth_summary.csv`
- `iris_event_gCMT_minus_analysed_map_data.csv`

The map is calculated as:

`gCMT result - analysed-depth result`

Therefore positive/blue means the gCMT depth produces a higher modelled structural loss than the analysed 14 km depth.

## Exact vulnerability function

The Iris script also plots the exact model function:

`MUR+CLBRS/LWAL/CDN+ERN/H:1/RES`

from GEM Global Vulnerability Model v2026.0.0.

Outputs:

- `outputs_gwfm/structural_vulnerability_curve.png`
- `outputs_gwfm/structural_vulnerability_curve_points.csv`

The CSV is written directly from the XML-loaded intensity-measure levels and mean loss ratios.
