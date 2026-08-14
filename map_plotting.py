import json
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


TURKEY_BOUNDARY_FILE = (
    Path(__file__).resolve().parent / "data" / "turkey_boundary.geojson"
)
TURKEY_BORDER_COLOR = "black"
ZERO_PGA_COLOR = "#bdbdbd"
POSITIVE_PGA_COLOR_MAP = "viridis"
VS30_COLOR_MAP = "viridis"


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


def plot_vs30_map(exposure, output_file, vs30_column="vs30_m_s"):
    required_columns = {"longitude", "latitude", vs30_column}
    missing_columns = required_columns.difference(exposure.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Vs30 map data is missing columns: {missing_text}.")

    try:
        longitudes = exposure["longitude"].to_numpy(float)
        latitudes = exposure["latitude"].to_numpy(float)
        vs30_values = exposure[vs30_column].to_numpy(float)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Vs30 map coordinates and values must be numeric."
        ) from error

    if len(exposure) == 0:
        raise ValueError("Vs30 map data cannot be empty.")
    if not np.isfinite(longitudes).all() or not np.isfinite(latitudes).all():
        raise ValueError("Vs30 map coordinates must be finite.")
    if not np.isfinite(vs30_values).all():
        raise ValueError("Vs30 map values must be finite.")
    if (vs30_values <= 0.0).any():
        raise ValueError("Vs30 map values must be greater than zero.")

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)
    points = ax.scatter(
        longitudes,
        latitudes,
        c=vs30_values,
        cmap=VS30_COLOR_MAP,
        s=38,
        edgecolor="black",
        linewidth=0.25,
        zorder=3,
    )

    if "vs30_status" in exposure.columns:
        nearest_mask = exposure["vs30_status"].astype(str) == "nearest_valid"
        if nearest_mask.any():
            ax.scatter(
                longitudes[nearest_mask],
                latitudes[nearest_mask],
                s=75,
                facecolors="none",
                edgecolors="red",
                linewidth=1.0,
                label="Nearest valid raster cell",
                zorder=4,
            )
            ax.legend()

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Vs30 values at exposure-grid locations")
    ax.set_aspect(1 / np.cos(np.deg2rad(float(latitudes.mean()))))
    colorbar = fig.colorbar(points, ax=ax)
    colorbar.set_label("Vs30 (m/s)")
    fig.tight_layout()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return output_path
