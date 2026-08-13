import json
from pathlib import Path

import matplotlib.colors as mcolors
import numpy as np


TURKEY_BOUNDARY_FILE = (
    Path(__file__).resolve().parent / "data" / "turkey_boundary.geojson"
)
TURKEY_BORDER_COLOR = "black"
ZERO_PGA_COLOR = "#bdbdbd"
POSITIVE_PGA_COLOR_MAP = "viridis"


def load_turkey_boundary_rings(boundary_file=TURKEY_BOUNDARY_FILE):
    boundary_path = Path(boundary_file)

    try:
        with boundary_path.open(encoding="utf-8") as boundary_stream:
            boundary = json.load(boundary_stream)
    except OSError as error:
        raise ValueError(
            f"Could not read Turkey boundary file: {boundary_path}."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Turkey boundary file is not valid GeoJSON: {boundary_path}."
        ) from error

    if boundary.get("type") == "FeatureCollection":
        features = boundary.get("features", [])
    elif boundary.get("type") == "Feature":
        features = [boundary]
    else:
        raise ValueError("Turkey boundary must be a GeoJSON feature collection.")

    rings = []

    for feature in features:
        geometry = feature.get("geometry") or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if geometry_type == "Polygon":
            polygons = [coordinates]
        elif geometry_type == "MultiPolygon":
            polygons = coordinates
        else:
            raise ValueError(
                "Turkey boundary geometry must be Polygon or MultiPolygon."
            )

        for polygon in polygons or []:
            if not polygon:
                raise ValueError("Turkey boundary contains an empty polygon.")

            try:
                exterior_ring = np.asarray(polygon[0], dtype=float)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "Turkey boundary coordinates must be numeric."
                ) from error

            if exterior_ring.ndim != 2 or exterior_ring.shape[1] != 2:
                raise ValueError(
                    "Turkey boundary rings must contain longitude/latitude pairs."
                )
            if len(exterior_ring) < 4:
                raise ValueError(
                    "Turkey boundary rings must contain at least four coordinates."
                )
            if not np.isfinite(exterior_ring).all():
                raise ValueError("Turkey boundary coordinates must be finite.")
            if not np.allclose(exterior_ring[0], exterior_ring[-1]):
                raise ValueError("Turkey boundary rings must be closed.")

            rings.append(exterior_ring)

    if not rings:
        raise ValueError("Turkey boundary does not contain any polygon rings.")

    return tuple(rings)


def plot_turkey_border(ax, boundary_file=TURKEY_BOUNDARY_FILE):
    lines = []

    for ring in load_turkey_boundary_rings(boundary_file):
        line, = ax.plot(
            ring[:, 0],
            ring[:, 1],
            color=TURKEY_BORDER_COLOR,
            linewidth=1.2,
            zorder=2,
        )
        lines.append(line)

    return tuple(lines)


def plot_pga_receiver_points(ax, map_results):
    required_columns = {
        "receiver_longitude",
        "receiver_latitude",
        "median_pga_g",
    }
    missing_columns = required_columns.difference(map_results.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"PGA map data is missing columns: {missing_text}.")

    try:
        longitudes = map_results["receiver_longitude"].to_numpy(float)
        latitudes = map_results["receiver_latitude"].to_numpy(float)
        pga_values = map_results["median_pga_g"].to_numpy(float)
    except (TypeError, ValueError) as error:
        raise ValueError("PGA map coordinates and values must be numeric.") from error

    if (
        not np.isfinite(longitudes).all()
        or not np.isfinite(latitudes).all()
    ):
        raise ValueError("PGA map coordinates must be finite.")
    if not np.isfinite(pga_values).all():
        raise ValueError("PGA map values must be finite.")
    if (pga_values < 0.0).any():
        raise ValueError("PGA map values cannot be negative.")

    zero_mask = pga_values == 0.0
    positive_mask = pga_values > 0.0

    if zero_mask.any():
        ax.scatter(
            longitudes[zero_mask],
            latitudes[zero_mask],
            color=ZERO_PGA_COLOR,
            s=30,
            edgecolor="black",
            linewidth=0.2,
            label="PGA = 0 g",
            zorder=3,
        )

    if not positive_mask.any():
        return None

    positive_pga = pga_values[positive_mask]
    minimum_pga = float(positive_pga.min())
    maximum_pga = float(positive_pga.max())

    if minimum_pga == maximum_pga:
        normalisation = mcolors.Normalize(vmin=0.0, vmax=maximum_pga)
    else:
        normalisation = mcolors.LogNorm(
            vmin=minimum_pga,
            vmax=maximum_pga,
        )

    return ax.scatter(
        longitudes[positive_mask],
        latitudes[positive_mask],
        c=positive_pga,
        cmap=POSITIVE_PGA_COLOR_MAP,
        norm=normalisation,
        s=30,
        edgecolor="black",
        linewidth=0.2,
        zorder=3,
    )
