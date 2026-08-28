from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

from map_plotting import load_turkey_boundary_rings, plot_turkey_border
from vs30_sampling import sample_vs30_raster


FULL_RASTER_FILE = Path("data/external/TRVs30GeoM_3Arcsec.tif")
MODEL_RECEIVER_FILE = Path("data/turkey_50km_land_grid_vs30.csv")

OUTPUT_FOLDER = Path("outputs_gwfm/vs30_raster_comparison")
PATTERN_FIGURE_FILE = OUTPUT_FOLDER / "vs30_full_raster_vs_sampled_receivers.png"
DIFFERENCE_FIGURE_FILE = OUTPUT_FOLDER / "vs30_3arcsec_minus_model_receivers.png"
RECEIVER_COMPARISON_FILE = OUTPUT_FOLDER / "vs30_3arcsec_receiver_comparison.csv"
SUMMARY_FILE = OUTPUT_FOLDER / "vs30_raster_comparison_summary.csv"

INPUT_CRS = "EPSG:4326"
MINIMUM_VS30_M_S = 150.0
MAXIMUM_VS30_M_S = 1200.0
MAXIMUM_FALLBACK_DISTANCE_M = 10000.0

# The 1.2 GB source raster is used directly. Only the display image is
# downsampled; receiver values are sampled from the native raster.
DISPLAY_WIDTH_PIXELS = 1400
MAP_PADDING_DEGREES = 0.25
VS30_CMAP = "viridis"
DIFFERENCE_CMAP = "RdBu_r"


def load_model_receivers():
    receivers = pd.read_csv(MODEL_RECEIVER_FILE)

    required = {
        "location_id",
        "longitude",
        "latitude",
        "vs30_m_s",
        "vs30_status",
    }
    missing = required.difference(receivers.columns)
    if missing:
        raise ValueError(
            "Model receiver file is missing columns: "
            + ", ".join(sorted(missing))
        )

    if len(receivers) != 311:
        raise ValueError(
            f"Expected 311 model receiver rows, found {len(receivers)}."
        )
    if receivers["location_id"].duplicated().any():
        raise ValueError("Model receiver IDs are not unique.")

    for column in ["longitude", "latitude", "vs30_m_s"]:
        receivers[column] = pd.to_numeric(receivers[column], errors="coerce")
        if not np.isfinite(receivers[column]).all():
            raise ValueError(f"{column} contains non-finite values.")

    status_counts = receivers["vs30_status"].value_counts().to_dict()
    if status_counts.get("direct", 0) != 304:
        raise ValueError(
            "Expected 304 direct Vs30 receiver values in the validated "
            f"model grid, found {status_counts.get('direct', 0)}."
        )
    if status_counts.get("nearest_valid", 0) != 7:
        raise ValueError(
            "Expected 7 nearest-valid Vs30 receiver values in the validated "
            f"model grid, found {status_counts.get('nearest_valid', 0)}."
        )

    return receivers


def sample_native_3arcsec_at_receivers(model_receivers):
    locations = model_receivers[["location_id", "longitude", "latitude"]].copy()

    sampled = sample_vs30_raster(
        locations,
        FULL_RASTER_FILE,
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
        print("\nUnresolved 3-arcsec receiver samples:")
        print(sampled.loc[unresolved].to_string(index=False))
        raise ValueError(
            "Some 311 receiver locations do not have a usable 3-arcsec "
            "Vs30 value within the existing 10 km fallback limit."
        )

    sampled = sampled.rename(
        columns={
            "vs30_m_s": "vs30_3arcsec_m_s",
            "vs30_status": "vs30_3arcsec_status",
            "direct_status": "vs30_3arcsec_direct_status",
            "raster_row": "vs30_3arcsec_raster_row",
            "raster_column": "vs30_3arcsec_raster_column",
            "fallback_distance_m": "vs30_3arcsec_fallback_distance_m",
            "source_raster": "vs30_3arcsec_source_raster",
            "source_raster_md5": "vs30_3arcsec_source_raster_md5",
        }
    )

    return sampled


def build_receiver_comparison(model_receivers, sampled_3arcsec):
    model_columns = [
        "location_id",
        "longitude",
        "latitude",
        "vs30_m_s",
        "vs30_status",
    ]
    if "fallback_distance_m" in model_receivers.columns:
        model_columns.append("fallback_distance_m")
    if "source_raster" in model_receivers.columns:
        model_columns.append("source_raster")
    if "source_raster_md5" in model_receivers.columns:
        model_columns.append("source_raster_md5")

    model = model_receivers[model_columns].copy().rename(
        columns={
            "vs30_m_s": "vs30_model_9arcsec_m_s",
            "vs30_status": "vs30_model_9arcsec_status",
            "fallback_distance_m": "vs30_model_9arcsec_fallback_distance_m",
            "source_raster": "vs30_model_source_raster",
            "source_raster_md5": "vs30_model_source_raster_md5",
        }
    )

    highres_columns = [
        "location_id",
        "vs30_3arcsec_m_s",
        "vs30_3arcsec_status",
        "vs30_3arcsec_direct_status",
        "vs30_3arcsec_raster_row",
        "vs30_3arcsec_raster_column",
        "vs30_3arcsec_fallback_distance_m",
        "vs30_3arcsec_source_raster",
        "vs30_3arcsec_source_raster_md5",
    ]

    comparison = model.merge(
        sampled_3arcsec[highres_columns],
        on="location_id",
        how="left",
        validate="one_to_one",
    )

    if len(comparison) != 311:
        raise ValueError(
            f"Expected 311 merged receiver rows, found {len(comparison)}."
        )

    comparison["vs30_3arcsec_minus_model_m_s"] = (
        comparison["vs30_3arcsec_m_s"]
        - comparison["vs30_model_9arcsec_m_s"]
    )
    comparison["vs30_absolute_difference_m_s"] = (
        comparison["vs30_3arcsec_minus_model_m_s"].abs()
    )
    comparison["vs30_percent_difference"] = (
        100.0
        * comparison["vs30_3arcsec_minus_model_m_s"]
        / comparison["vs30_model_9arcsec_m_s"]
    )

    return comparison


def turkey_plot_bounds():
    rings = load_turkey_boundary_rings()
    all_points = np.vstack(rings)

    left = float(all_points[:, 0].min()) - MAP_PADDING_DEGREES
    right = float(all_points[:, 0].max()) + MAP_PADDING_DEGREES
    bottom = float(all_points[:, 1].min()) - MAP_PADDING_DEGREES
    top = float(all_points[:, 1].max()) + MAP_PADDING_DEGREES

    return (left, bottom, right, top), rings


def mask_outside_turkey(data, bounds, rings):
    left, bottom, right, top = bounds
    height, width = data.shape

    x_coordinates = left + (
        np.arange(width, dtype=float) + 0.5
    ) * ((right - left) / width)
    y_coordinates = top - (
        np.arange(height, dtype=float) + 0.5
    ) * ((top - bottom) / height)

    xx, yy = np.meshgrid(x_coordinates, y_coordinates)
    points = np.column_stack((xx.ravel(), yy.ravel()))

    inside = np.zeros(len(points), dtype=bool)
    for ring in rings:
        inside |= MplPath(ring).contains_points(points)

    inside = inside.reshape(data.shape)
    masked = data.copy()
    masked[~inside] = np.nan
    return masked


def read_display_raster():
    bounds, rings = turkey_plot_bounds()
    left, bottom, right, top = bounds

    width = DISPLAY_WIDTH_PIXELS
    aspect_ratio = (top - bottom) / (right - left)
    height = max(1, int(round(width * aspect_ratio)))

    destination = np.full((height, width), np.nan, dtype=np.float32)
    destination_transform = from_bounds(
        left,
        bottom,
        right,
        top,
        width,
        height,
    )

    with rasterio.open(FULL_RASTER_FILE) as raster:
        if raster.count != 1:
            raise ValueError("The 3-arcsec Vs30 raster must have one band.")
        if raster.crs is None:
            raise ValueError("The 3-arcsec Vs30 raster has no CRS.")
        if not raster.crs.is_projected:
            raise ValueError(
                "The 3-arcsec Vs30 raster is expected to use a projected CRS."
            )

        lonlat_bounds = transform_bounds(
            raster.crs,
            INPUT_CRS,
            *raster.bounds,
            densify_pts=21,
        )

        reproject(
            source=rasterio.band(raster, 1),
            destination=destination,
            src_transform=raster.transform,
            src_crs=raster.crs,
            src_nodata=raster.nodata,
            dst_transform=destination_transform,
            dst_crs=INPUT_CRS,
            dst_nodata=np.nan,
            resampling=Resampling.average,
            init_dest_nodata=True,
        )

        metadata = {
            "raster_crs": raster.crs.to_string(),
            "raster_width": raster.width,
            "raster_height": raster.height,
            "raster_resolution_x": abs(float(raster.res[0])),
            "raster_resolution_y": abs(float(raster.res[1])),
            "raster_nodata": raster.nodata,
            "raster_lonlat_left": lonlat_bounds[0],
            "raster_lonlat_bottom": lonlat_bounds[1],
            "raster_lonlat_right": lonlat_bounds[2],
            "raster_lonlat_top": lonlat_bounds[3],
        }

    unusable = (
        ~np.isfinite(destination)
        | (destination <= MINIMUM_VS30_M_S)
        | (destination >= MAXIMUM_VS30_M_S)
    )
    destination[unusable] = np.nan
    destination = mask_outside_turkey(destination, bounds, rings)

    if not np.isfinite(destination).any():
        raise ValueError(
            "No valid 3-arcsec Vs30 values remain in the Turkey plotting area."
        )

    return destination, bounds, metadata


def plot_pattern_comparison(display_raster, bounds, model_receivers):
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    left, bottom, right, top = bounds
    normalisation = mcolors.Normalize(
        vmin=MINIMUM_VS30_M_S,
        vmax=MAXIMUM_VS30_M_S,
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(16, 6.5),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )

    raster_image = axes[0].imshow(
        display_raster,
        extent=(left, right, bottom, top),
        origin="upper",
        cmap=VS30_CMAP,
        norm=normalisation,
        interpolation="nearest",
        zorder=1,
    )
    plot_turkey_border(axes[0])
    axes[0].set_title(
        "TRVs30GeoM 3-arcsec raster\n"
        "(full raster source, downsampled only for display)"
    )

    axes[1].scatter(
        model_receivers["longitude"],
        model_receivers["latitude"],
        c=model_receivers["vs30_m_s"],
        cmap=VS30_CMAP,
        norm=normalisation,
        s=32,
        edgecolor="black",
        linewidth=0.2,
        zorder=3,
    )
    plot_turkey_border(axes[1])

    fallback = model_receivers["vs30_status"].astype(str) == "nearest_valid"
    axes[1].scatter(
        model_receivers.loc[fallback, "longitude"],
        model_receivers.loc[fallback, "latitude"],
        facecolors="none",
        edgecolors="red",
        s=95,
        linewidth=1.2,
        label="Nearest-valid model Vs30",
        zorder=4,
    )
    axes[1].legend(loc="upper right")
    axes[1].set_title(
        "311 Vs30 receiver values used by the model\n"
        "(current 9-arcsec sampled source)"
    )

    for axis in axes:
        axis.set_xlim(left, right)
        axis.set_ylim(bottom, top)
        axis.set_xlabel("Longitude")
        axis.set_ylabel("Latitude")
        axis.grid(alpha=0.2)

    colourbar = fig.colorbar(
        raster_image,
        ax=axes,
        location="right",
        fraction=0.035,
        pad=0.02,
    )
    colourbar.set_label("Vs30 (m/s)")

    fig.suptitle(
        "Turkey Vs30: high-resolution raster pattern versus model receiver sampling",
        fontsize=15,
    )
    fig.savefig(PATTERN_FIGURE_FILE, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_receiver_difference(comparison):
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    differences = comparison["vs30_3arcsec_minus_model_m_s"].to_numpy(float)
    maximum_absolute = float(np.max(np.abs(differences)))
    if maximum_absolute == 0.0:
        maximum_absolute = 1.0

    normalisation = mcolors.TwoSlopeNorm(
        vmin=-maximum_absolute,
        vcenter=0.0,
        vmax=maximum_absolute,
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)

    points = ax.scatter(
        comparison["longitude"],
        comparison["latitude"],
        c=differences,
        cmap=DIFFERENCE_CMAP,
        norm=normalisation,
        s=38,
        edgecolor="black",
        linewidth=0.2,
        zorder=3,
    )

    fallback = (
        comparison["vs30_model_9arcsec_status"].astype(str)
        == "nearest_valid"
    )
    ax.scatter(
        comparison.loc[fallback, "longitude"],
        comparison.loc[fallback, "latitude"],
        facecolors="none",
        edgecolors="black",
        s=105,
        linewidth=1.1,
        label="7 nearest-valid model receivers",
        zorder=4,
    )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        "Receiver-level Vs30 difference\n"
        "TRVs30GeoM 3 arcsec minus current model 9-arcsec receiver value"
    )
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")

    colourbar = fig.colorbar(points, ax=ax)
    colourbar.set_label("Vs30 difference (m/s): 3 arcsec minus model value")

    fig.tight_layout()
    fig.savefig(DIFFERENCE_FIGURE_FILE, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_summary(comparison, raster_metadata):
    difference = comparison["vs30_3arcsec_minus_model_m_s"]
    absolute = comparison["vs30_absolute_difference_m_s"]

    model_status = comparison["vs30_model_9arcsec_status"].value_counts()
    highres_status = comparison["vs30_3arcsec_status"].value_counts()

    model_values = comparison["vs30_model_9arcsec_m_s"]
    highres_values = comparison["vs30_3arcsec_m_s"]

    row = {
        "full_raster_file": FULL_RASTER_FILE.name,
        "model_receiver_file": MODEL_RECEIVER_FILE.name,
        "comparison_note": (
            "Full raster is TRVs30GeoM 3 arcsec; current 311 model receiver "
            "values were originally sampled from the 9-arcsec product."
        ),
        "receiver_count": len(comparison),
        "model_9arcsec_direct_count": int(model_status.get("direct", 0)),
        "model_9arcsec_nearest_valid_count": int(
            model_status.get("nearest_valid", 0)
        ),
        "raster_3arcsec_direct_count": int(highres_status.get("direct", 0)),
        "raster_3arcsec_nearest_valid_count": int(
            highres_status.get("nearest_valid", 0)
        ),
        "model_9arcsec_vs30_min_m_s": float(model_values.min()),
        "model_9arcsec_vs30_max_m_s": float(model_values.max()),
        "raster_3arcsec_receiver_vs30_min_m_s": float(highres_values.min()),
        "raster_3arcsec_receiver_vs30_max_m_s": float(highres_values.max()),
        "median_signed_difference_m_s": float(difference.median()),
        "median_absolute_difference_m_s": float(absolute.median()),
        "mean_absolute_difference_m_s": float(absolute.mean()),
        "p95_absolute_difference_m_s": float(absolute.quantile(0.95)),
        "maximum_absolute_difference_m_s": float(absolute.max()),
        "pearson_correlation": float(
            model_values.corr(highres_values, method="pearson")
        ),
        "spearman_correlation": float(
            model_values.corr(highres_values, method="spearman")
        ),
        "receivers_abs_difference_le_25_m_s": int((absolute <= 25.0).sum()),
        "receivers_abs_difference_le_50_m_s": int((absolute <= 50.0).sum()),
    }
    row.update(raster_metadata)

    return pd.DataFrame([row])


def main():
    if not FULL_RASTER_FILE.exists():
        raise FileNotFoundError(
            f"Missing full raster: {FULL_RASTER_FILE}"
        )
    if not MODEL_RECEIVER_FILE.exists():
        raise FileNotFoundError(
            f"Missing model receiver file: {MODEL_RECEIVER_FILE}"
        )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    print("Loading validated 311 model receiver values...")
    model_receivers = load_model_receivers()

    print(
        "Sampling the native 3-arcsec raster at all 311 receiver locations..."
    )
    print(
        "Note: the existing sampler calculates an MD5 checksum of the "
        "1.2 GB raster, so this step can take a little time."
    )
    sampled_3arcsec = sample_native_3arcsec_at_receivers(model_receivers)

    comparison = build_receiver_comparison(
        model_receivers,
        sampled_3arcsec,
    )
    comparison.to_csv(RECEIVER_COMPARISON_FILE, index=False)

    print("Reading the full 3-arcsec raster for the presentation figure...")
    display_raster, bounds, raster_metadata = read_display_raster()

    plot_pattern_comparison(
        display_raster,
        bounds,
        model_receivers,
    )
    plot_receiver_difference(comparison)

    summary = build_summary(comparison, raster_metadata)
    summary.to_csv(SUMMARY_FILE, index=False)

    print("\nVs30 full-raster comparison complete.")
    print("Full raster source:", FULL_RASTER_FILE)
    print("Model receiver source file:", MODEL_RECEIVER_FILE)
    print("Receiver rows:", len(comparison))
    print("Current model status counts:")
    print(
        comparison["vs30_model_9arcsec_status"]
        .value_counts()
        .to_string()
    )
    print("3-arcsec sample status counts:")
    print(
        comparison["vs30_3arcsec_status"]
        .value_counts()
        .to_string()
    )
    print(
        "Current model Vs30 range:",
        round(comparison["vs30_model_9arcsec_m_s"].min(), 1),
        "to",
        round(comparison["vs30_model_9arcsec_m_s"].max(), 1),
        "m/s",
    )
    print(
        "3-arcsec receiver Vs30 range:",
        round(comparison["vs30_3arcsec_m_s"].min(), 1),
        "to",
        round(comparison["vs30_3arcsec_m_s"].max(), 1),
        "m/s",
    )
    print(
        "Median signed 3-arcsec minus model difference:",
        round(comparison["vs30_3arcsec_minus_model_m_s"].median(), 2),
        "m/s",
    )
    print(
        "Median absolute difference:",
        round(comparison["vs30_absolute_difference_m_s"].median(), 2),
        "m/s",
    )
    print(
        "Mean absolute difference:",
        round(comparison["vs30_absolute_difference_m_s"].mean(), 2),
        "m/s",
    )
    print(
        "95th percentile absolute difference:",
        round(
            comparison["vs30_absolute_difference_m_s"].quantile(0.95),
            2,
        ),
        "m/s",
    )
    print(
        "Pearson correlation:",
        round(
            comparison["vs30_model_9arcsec_m_s"].corr(
                comparison["vs30_3arcsec_m_s"],
                method="pearson",
            ),
            4,
        ),
    )
    print(
        "Spearman correlation:",
        round(
            comparison["vs30_model_9arcsec_m_s"].corr(
                comparison["vs30_3arcsec_m_s"],
                method="spearman",
            ),
            4,
        ),
    )
    print("\nSaved:")
    print(PATTERN_FIGURE_FILE)
    print(DIFFERENCE_FIGURE_FILE)
    print(RECEIVER_COMPARISON_FILE)
    print(SUMMARY_FILE)
    print(
        "\nImportant: this does not replace the model's existing 9-arcsec "
        "Vs30 values. It compares them with the 3-arcsec raster."
    )


if __name__ == "__main__":
    main()
