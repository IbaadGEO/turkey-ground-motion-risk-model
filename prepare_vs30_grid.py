from pathlib import Path

import pandas as pd

from map_plotting import plot_vs30_map
from vs30_sampling import sample_vs30_raster


EXPOSURE_FILE = Path("data/turkey_50km_land_grid.csv")
VS30_RASTER_FILE = Path("data/external/TRVs30GeoM_9Arcsec.tif")
OUTPUT_FILE = Path("data/turkey_50km_land_grid_vs30.csv")
MAP_OUTPUT_FILE = Path("outputs_gwfm/vs30_map.png")

INPUT_CRS = "EPSG:4326"
MINIMUM_VS30_M_S = 150.0
MAXIMUM_VS30_M_S = 1200.0
MAXIMUM_FALLBACK_DISTANCE_M = 10000.0


def main():
    exposure = pd.read_csv(EXPOSURE_FILE)
    sampled = sample_vs30_raster(
        exposure,
        VS30_RASTER_FILE,
        id_column="location_id",
        longitude_column="longitude",
        latitude_column="latitude",
        input_crs=INPUT_CRS,
        minimum_vs30=MINIMUM_VS30_M_S,
        maximum_vs30=MAXIMUM_VS30_M_S,
        maximum_fallback_distance_m=MAXIMUM_FALLBACK_DISTANCE_M,
    )

    unresolved = ~sampled["vs30_status"].isin(["direct", "nearest_valid"])
    if unresolved.any():
        print(sampled.loc[unresolved].to_string(index=False))
        raise ValueError("Some exposure locations do not have a usable Vs30 value.")

    sampled.to_csv(OUTPUT_FILE, index=False)
    plot_vs30_map(sampled, MAP_OUTPUT_FILE)

    print("Exposure locations:", len(sampled))
    print("Vs30 status counts:")
    print(sampled["vs30_status"].value_counts().to_string())
    print(
        "Vs30 range:",
        round(sampled["vs30_m_s"].min(), 1),
        "to",
        round(sampled["vs30_m_s"].max(), 1),
        "m/s",
    )
    print("Saved:", OUTPUT_FILE)
    print("Saved:", MAP_OUTPUT_FILE)


if __name__ == "__main__":
    main()
