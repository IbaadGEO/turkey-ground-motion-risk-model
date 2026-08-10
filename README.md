# Turkey ground-motion example

This code uses the Akkar et al. (2014) ground-motion model in OpenQuake.

It reads a small earthquake catalogue and a grid of exposure locations. It then uses a nested loop to calculate the distance from every earthquake to every location.

The code calculates:

- PGA
- PGV
- SA at 0.2 seconds
- SA at 1 second
- a provisional damage ratio based on PGA

## Files

The input CSV files are in the `data` folder.

The five-event catalogue is only a small example for testing the code. It is not the final gWFM catalogue.

## Running the code

Install the packages in `requirements.txt`, then run:

```text
python akkar_turkey_portfolio.py
```

The file paths, catalogue column names, Vs30 value and event used for the PGA map are listed near the top of the Python file. These can be edited when a different catalogue is used.

Results are saved in the `outputs` folder:

- `ground_motion_results.csv`
- `damage_ratios.csv`
- `exposure_and_earthquakes.png`
- `pga_map_<event_id>.png`

The vulnerability curve is provisional and should be replaced before the damage results are used as final results.
