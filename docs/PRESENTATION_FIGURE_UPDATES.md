# Presentation figure updates

This work keeps the validated 117-event production catalogue unchanged and adds a separate Elazığ-Sivrice case-study presentation analysis.

## Updated catalogue-wide figures

`presentation_figures.py` reads the existing numerical depth-sensitivity summary and regenerates:

- `pga_sensitivity_by_distance.png`
- `loss_sensitivity_by_distance.png`

Colour meaning is fixed across both figures:

- gCMT = blue
- ISC-EHB = orange

The loss figure uses solid lines for means and dashed lines for 95th percentiles. Both figures show sample sizes by distance bin.

## 2020 Elazığ-Sivrice event example

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

This case-study earthquake was selected by Iris from the waveform dataset used in the project.

Outputs:

- `elazig_sivrice_pga_vs_depth.png`
- `elazig_sivrice_analysed_minus_gCMT_loss_difference_map.png`
- `elazig_sivrice_complete_results.csv`
- `elazig_sivrice_depth_summary.csv`
- `elazig_sivrice_analysed_minus_gCMT_map_data.csv`

The map is calculated as:

`analysed-depth result - gCMT result`

Therefore negative/red means the shallower gCMT depth produces a higher modelled structural loss than the analysed 14 km depth.

## Exact vulnerability function

The Iris script also plots the exact model function:

`MUR+CLBRS/LWAL/CDN+ERN/H:1/RES`

from GEM Global Vulnerability Model v2026.0.0.

Outputs:

- `outputs_gwfm/structural_vulnerability_curve.png`
- `outputs_gwfm/structural_vulnerability_curve_points.csv`

The CSV is written directly from the XML-loaded intensity-measure levels and mean loss ratios.
