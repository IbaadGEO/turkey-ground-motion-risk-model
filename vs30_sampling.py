from hashlib import md5
from math import ceil, hypot
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.transform import xy
from rasterio.warp import transform
from rasterio.windows import Window


def file_md5(file_path):
    checksum = md5()
    with Path(file_path).open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest().upper()


def value_is_usable(value, nodata, minimum_vs30, maximum_vs30):
    if not np.isfinite(value):
        return False
    if nodata is not None and np.isclose(value, nodata):
        return False
    return minimum_vs30 < value < maximum_vs30


def nearest_usable_cell(
    raster,
    x_coordinate,
    y_coordinate,
    row,
    column,
    minimum_vs30,
    maximum_vs30,
    maximum_distance_m,
):
    x_pixel_size = hypot(raster.transform.a, raster.transform.b)
    y_pixel_size = hypot(raster.transform.d, raster.transform.e)
    metres_per_raster_unit = raster.crs.linear_units_factor[1]
    smallest_pixel_size_m = min(x_pixel_size, y_pixel_size) * metres_per_raster_unit
    search_radius = ceil(maximum_distance_m / smallest_pixel_size_m) + 1

    first_row = max(0, row - search_radius)
    last_row = min(raster.height, row + search_radius + 1)
    first_column = max(0, column - search_radius)
    last_column = min(raster.width, column + search_radius + 1)

    window = Window(
        first_column,
        first_row,
        last_column - first_column,
        last_row - first_row,
    )
    values = raster.read(1, window=window)
    usable = np.isfinite(values)
    if raster.nodata is not None:
        usable &= ~np.isclose(values, raster.nodata)
    usable &= values > minimum_vs30
    usable &= values < maximum_vs30

    local_rows, local_columns = np.where(usable)
    if len(local_rows) == 0:
        return None

    raster_rows = local_rows + first_row
    raster_columns = local_columns + first_column
    cell_centres = [
        xy(raster.transform, int(cell_row), int(cell_column), offset="center")
        for cell_row, cell_column in zip(raster_rows, raster_columns)
    ]
    distances_m = np.array(
        [
            hypot(cell_x - x_coordinate, cell_y - y_coordinate)
            * metres_per_raster_unit
            for cell_x, cell_y in cell_centres
        ]
    )

    nearest_index = int(distances_m.argmin())
    if distances_m[nearest_index] > maximum_distance_m:
        return None

    return {
        "vs30_m_s": float(values[local_rows[nearest_index], local_columns[nearest_index]]),
        "raster_row": int(raster_rows[nearest_index]),
        "raster_column": int(raster_columns[nearest_index]),
        "fallback_distance_m": float(distances_m[nearest_index]),
    }


def sample_vs30_raster(
    locations,
    raster_file,
    id_column,
    longitude_column,
    latitude_column,
    input_crs,
    minimum_vs30,
    maximum_vs30,
    maximum_fallback_distance_m,
):
    required_columns = [id_column, longitude_column, latitude_column]
    missing_columns = [
        column for column in required_columns if column not in locations.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing location columns: {missing_columns}")

    if locations[id_column].duplicated().any():
        duplicate_ids = locations.loc[
            locations[id_column].duplicated(keep=False), id_column
        ].tolist()
        raise ValueError(f"Duplicate location IDs: {duplicate_ids}")

    longitudes = pd.to_numeric(locations[longitude_column], errors="coerce")
    latitudes = pd.to_numeric(locations[latitude_column], errors="coerce")
    if not np.isfinite(longitudes).all() or not np.isfinite(latitudes).all():
        raise ValueError("Location coordinates must all be finite numbers.")

    raster_path = Path(raster_file)
    raster_checksum = file_md5(raster_path)
    input_coordinate_system = CRS.from_user_input(input_crs)
    rows = []

    with rasterio.open(raster_path) as raster:
        if raster.count != 1:
            raise ValueError("The Vs30 raster must contain one data band.")
        if raster.crs is None:
            raise ValueError("The Vs30 raster does not contain a coordinate system.")
        if not raster.crs.is_projected:
            raise ValueError("The Vs30 raster must use a projected coordinate system.")

        x_coordinates, y_coordinates = transform(
            input_coordinate_system,
            raster.crs,
            longitudes.tolist(),
            latitudes.tolist(),
        )

        for location_id, longitude, latitude, x_coordinate, y_coordinate in zip(
            locations[id_column],
            longitudes,
            latitudes,
            x_coordinates,
            y_coordinates,
        ):
            row, column = raster.index(x_coordinate, y_coordinate)
            result = {
                id_column: location_id,
                longitude_column: longitude,
                latitude_column: latitude,
                "vs30_m_s": np.nan,
                "vs30_status": "outside_raster",
                "direct_status": "outside_raster",
                "raster_row": np.nan,
                "raster_column": np.nan,
                "fallback_distance_m": np.nan,
                "source_raster": raster_path.name,
                "source_raster_md5": raster_checksum,
            }

            inside_raster = (
                0 <= row < raster.height and 0 <= column < raster.width
            )
            if inside_raster:
                value = float(
                    raster.read(
                        1,
                        window=Window(column, row, 1, 1),
                    )[0, 0]
                )
                result["raster_row"] = row
                result["raster_column"] = column

                is_nodata = (
                    not np.isfinite(value)
                    or (
                        raster.nodata is not None
                        and np.isclose(value, raster.nodata)
                    )
                )
                if is_nodata:
                    result["direct_status"] = "nodata"
                    result["vs30_status"] = "nodata"
                elif value_is_usable(
                    value,
                    raster.nodata,
                    minimum_vs30,
                    maximum_vs30,
                ):
                    result["vs30_m_s"] = value
                    result["vs30_status"] = "direct"
                    result["direct_status"] = "valid"
                else:
                    result["direct_status"] = "outside_model_range"
                    result["vs30_status"] = "outside_model_range"

            if inside_raster and result["vs30_status"] != "direct":
                nearest = nearest_usable_cell(
                    raster,
                    x_coordinate,
                    y_coordinate,
                    row,
                    column,
                    minimum_vs30,
                    maximum_vs30,
                    maximum_fallback_distance_m,
                )
                if nearest is not None:
                    result.update(nearest)
                    result["vs30_status"] = "nearest_valid"

            rows.append(result)

    return pd.DataFrame(rows)
