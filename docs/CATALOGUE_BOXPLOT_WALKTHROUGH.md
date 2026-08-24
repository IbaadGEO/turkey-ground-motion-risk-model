# Catalogue boxplot walkthrough

The catalogue figure compares the model results obtained with gWFM, ISC-EHB
and gCMT earthquake depths. The plotting code is in
`catalogue_distribution_plots.py`. It reads the compact results table produced
by the main analysis, so it does not rerun the ground-motion or vulnerability
calculations.

## What is plotted

The input table has one row for each earthquake and depth source. The script
keeps the 90 earthquakes that have a valid depth in all three catalogues. For
each earthquake-catalogue pair, it uses:

- `maximum_pga_g`, the highest site-level median PGA among the 311 receivers;
- `maximum_structural_loss_ratio`, the highest mean structural loss ratio among
  the same receivers.

This gives each earthquake one observation per catalogue. Using the 270
event-catalogue rows, rather than treating 83,970 receiver rows as independent
earthquakes, keeps the comparison balanced. The plotted values are saved in
`outputs_gwfm/depth_sensitivity_analysis/catalogue_boxplot_event_maxima.csv`.

## How the boxes and points are drawn

Matplotlib's `boxplot` function draws one box for each catalogue. The black
line is the median, the box covers the interquartile range, and the whiskers
extend to 1.5 times that range. Every earthquake is then added with `scatter`.
A fixed random seed gives the points a small horizontal offset, which makes
overlapping values easier to see and keeps the layout the same each time the
script is run.

The boxplot's separate outlier symbols are switched off because the scatter
layer already shows every earthquake. No results are removed by this setting.

PGA is shown on a logarithmic vertical scale because its values span several
orders of magnitude. Structural loss uses a symmetric-log scale with a small
linear region around zero. This keeps exact zeros on the plot while separating
the small positive values from the larger tail.

A violin plot was considered but not used. Between 62 and 65 of the 90 event
maxima are exactly zero, depending on the catalogue. Smoothing those repeated
zeros into a density shape would give a less direct account of the model
output. The boxplot and individual points show the zero mass and the positive
tail separately.

## Reproducing the figure

Run the main model first if the compact results table is missing:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

Then generate the figure and its supporting data:

```powershell
python catalogue_distribution_plots.py
```

The command writes these files:

- `outputs_gwfm/depth_sensitivity_analysis/catalogue_pga_loss_boxplots.png`
- `outputs_gwfm/depth_sensitivity_analysis/catalogue_boxplot_event_maxima.csv`
- `outputs_gwfm/depth_sensitivity_analysis/catalogue_boxplot_summary.csv`

The summary CSV records the quartiles, largest value and number of exact-zero
loss events for each catalogue. These values can be used to check the figure
without reading measurements from the image.
