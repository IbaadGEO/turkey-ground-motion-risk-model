"""Create regularly spaced exposure points inside the Turkey boundary."""

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as PlotPath
from rasterio.warp import transform

from map_plotting import TURKEY_BOUNDARY_FILE, load_turkey_boundary_rings


GEOGRAPHIC_CRS = "EPSG:4326"
GRID_CRS = "EPSG:3035"


def _aligned_coordinates(minimum, maximum, spacing_m):
    first = np.floor(minimum / spacing_m) * spacing_m
    last = np.ceil(maximum / spacing_m) * spacing_m
    return np.arange(first, last + spacing_m, spacing_m)


def generate_turkey_land_grid(
    spacing_km,
    boundary_file=Path(TURKEY_BOUNDARY_FILE),
):
    """Return an EPSG:3035-aligned point grid clipped to Turkey's land area.

    The same method recreates all 311 points in the existing 50 km grid. Grid
    points are ordered south-to-north and then west-to-east so location IDs are
    deterministic.
    """

    spacing_km = float(spacing_km)
    if not np.isfinite(spacing_km) or spacing_km <= 0.0:
        raise ValueError("Grid spacing must be a positive number of kilometres.")

    rings = load_turkey_boundary_rings(boundary_file)
    all_coordinates = np.vstack(rings)
    boundary_eastings, boundary_northings = transform(
        GEOGRAPHIC_CRS,
        GRID_CRS,
        all_coordinates[:, 0].tolist(),
        all_coordinates[:, 1].tolist(),
    )

    spacing_m = spacing_km * 1000.0
    eastings = _aligned_coordinates(
        min(boundary_eastings),
        max(boundary_eastings),
        spacing_m,
    )
    northings = _aligned_coordinates(
        min(boundary_northings),
        max(boundary_northings),
        spacing_m,
    )
    easting_grid, northing_grid = np.meshgrid(eastings, northings)
    candidate_eastings = easting_grid.ravel()
    candidate_northings = northing_grid.ravel()

    longitudes, latitudes = transform(
        GRID_CRS,
        GEOGRAPHIC_CRS,
        candidate_eastings.tolist(),
        candidate_northings.tolist(),
    )
    geographic_points = np.column_stack((longitudes, latitudes))

    on_land = np.zeros(len(geographic_points), dtype=bool)
    for ring in rings:
        on_land |= PlotPath(ring).contains_points(
            geographic_points,
            radius=1e-12,
        )

    grid = pd.DataFrame(
        {
            "longitude": np.asarray(longitudes)[on_land],
            "latitude": np.asarray(latitudes)[on_land],
            "easting_m": candidate_eastings[on_land],
            "northing_m": candidate_northings[on_land],
        }
    )
    grid.insert(0, "location_id", np.arange(1, len(grid) + 1))
    return grid
