import matplotlib.colors as mcolors
import numpy as np


ZERO_PGA_COLOR = "#bdbdbd"
POSITIVE_PGA_COLOR_MAP = "turbo"


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
    )
