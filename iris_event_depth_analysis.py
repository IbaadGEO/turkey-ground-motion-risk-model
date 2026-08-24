"""Generate 2020 Elazığ-Sivrice presentation results using the project's existing GMPE and vulnerability model."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from akkar_turkey_portfolio_gwfm import (
    VULNERABILITY_FUNCTION_ID,
    VULNERABILITY_MODEL_VERSION,
    calculate_ground_motion,
    calculate_structural_loss,
    haversine_distance_km,
    load_inputs,
)
from map_plotting import plot_turkey_border


OUTPUT_FOLDER = Path("outputs_gwfm") / "iris_event_analysis"
VULNERABILITY_FIGURE = Path("outputs_gwfm") / "structural_vulnerability_curve.png"
VULNERABILITY_POINTS_CSV = Path("outputs_gwfm") / "structural_vulnerability_curve_points.csv"

IRIS_EVENT = {
    "event_id": "2020024175513",
    "origin_time": pd.Timestamp("2020-01-24 17:55:13"),
    "magnitude": 6.7,
    "magnitude_type": "Mww",
    # Representative strike-slip rake from the preferred USGS Mww moment tensor, NP2.
    "rake": -12.0,
    "latitude": 38.3897,
    "longitude": 39.0883,
}

DEPTH_SCENARIOS = [
    {"depth_source": "wilber3_usgs", "depth_label": "Wilber3 / USGS", "depth_km": 10.0},
    {"depth_source": "global_cmt", "depth_label": "gCMT", "depth_km": 12.0},
    {"depth_source": "analysed", "depth_label": "Analysed", "depth_km": 14.0},
]

REFERENCE_SOURCE = "analysed"
COMPARISON_SOURCE = "global_cmt"
MAP_MAX_REPI_KM = 150.0


def build_scenarios(exposure):
    exposure = exposure.reset_index(drop=True).copy()
    repi = np.asarray(
        haversine_distance_km(
            IRIS_EVENT["latitude"],
            IRIS_EVENT["longitude"],
            exposure["latitude"],
            exposure["longitude"],
        ),
        dtype=float,
    )

    rows = []
    for depth in DEPTH_SCENARIOS:
        rhyp = np.hypot(repi, depth["depth_km"])
        for index, location in exposure.iterrows():
            rows.append(
                {
                    "event_id": IRIS_EVENT["event_id"],
                    "origin_time": IRIS_EVENT["origin_time"],
                    "magnitude": IRIS_EVENT["magnitude"],
                    "magnitude_type": IRIS_EVENT["magnitude_type"],
                    "rake": IRIS_EVENT["rake"],
                    "source_latitude": IRIS_EVENT["latitude"],
                    "source_longitude": IRIS_EVENT["longitude"],
                    "depth_source": depth["depth_source"],
                    "depth_label": depth["depth_label"],
                    "source_depth_km": depth["depth_km"],
                    "location_id": location["location_id"],
                    "receiver_latitude": location["latitude"],
                    "receiver_longitude": location["longitude"],
                    "vs30": location["vs30"],
                    "repi_km": float(repi[index]),
                    "rhypo_km": float(rhyp[index]),
                    "source_within_30_km": depth["depth_km"] <= 30.0,
                    "within_200_km": float(rhyp[index]) <= 200.0,
                }
            )

    scenarios = pd.DataFrame(rows)
    expected = len(DEPTH_SCENARIOS) * len(exposure)
    if len(scenarios) != expected:
        raise ValueError(f"Expected {expected} Elazığ-Sivrice scenario rows, found {len(scenarios)}.")
    return scenarios


def calculate_outputs():
    _, _, exposure, vulnerability = load_inputs()
    scenarios = build_scenarios(exposure)
    ground_motion = calculate_ground_motion(scenarios)
    structural_loss = calculate_structural_loss(ground_motion, vulnerability)

    expected = len(DEPTH_SCENARIOS) * len(exposure)
    if len(structural_loss) != expected:
        raise ValueError(
            f"Expected {expected} Elazığ-Sivrice structural-loss rows, found {len(structural_loss)}."
        )
    if (structural_loss["median_pga_g"] <= 0.0).any():
        raise ValueError("Every Elazığ-Sivrice PGA value must be positive.")
    if not structural_loss["structural_loss_ratio_mean"].between(
        0.0, 1.0, inclusive="both"
    ).all():
        raise ValueError("Iris structural loss ratios must lie between 0 and 1.")

    return structural_loss, vulnerability


def summarise_by_depth(results):
    return (
        results.groupby(
            ["depth_source", "depth_label", "source_depth_km"],
            sort=False,
        )
        .agg(
            receiver_count=("location_id", "size"),
            receivers_within_150_km=(
                "repi_km",
                lambda values: int((values <= MAP_MAX_REPI_KM).sum()),
            ),
            receivers_within_200_km=("within_200_km", "sum"),
            minimum_repi_km=("repi_km", "min"),
            minimum_rhypo_km=("rhypo_km", "min"),
            median_pga_g=("median_pga_g", "median"),
            mean_pga_g=("median_pga_g", "mean"),
            maximum_pga_g=("median_pga_g", "max"),
            mean_structural_loss_ratio=("structural_loss_ratio_mean", "mean"),
            maximum_structural_loss_ratio=("structural_loss_ratio_mean", "max"),
            locations_with_nonzero_structural_loss=(
                "structural_loss_ratio_mean",
                lambda values: int((values > 0.0).sum()),
            ),
        )
        .reset_index()
    )


def nearest_receiver_rows(results):
    nearest_id = results.sort_values("repi_km").iloc[0]["location_id"]
    rows = results[results["location_id"] == nearest_id].copy()
    order = {"wilber3_usgs": 0, "global_cmt": 1, "analysed": 2}
    rows["_depth_order"] = rows["depth_source"].map(order)
    return rows.sort_values("_depth_order").drop(columns="_depth_order")


def plot_pga_vs_depth(results):
    nearest = nearest_receiver_rows(results)
    repi = float(nearest["repi_km"].iloc[0])
    vs30 = float(nearest["vs30"].iloc[0])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(
        nearest["source_depth_km"],
        nearest["median_pga_g"],
        marker="o",
        color="tab:blue",
        linewidth=2.2,
    )

    for _, row in nearest.iterrows():
        if row["depth_source"] == "wilber3_usgs":
            label_offset = -12
            label_va = "top"
        else:
            label_offset = 9
            label_va = "bottom"

        ax.annotate(
            f'{row["depth_label"]}\n{row["median_pga_g"]:.3f} g',
            (row["source_depth_km"], row["median_pga_g"]),
            xytext=(0, label_offset),
            textcoords="offset points",
            ha="center",
            va=label_va,
            fontsize=9,
        )

    ax.set_xlabel("Source depth used in model (km)")
    ax.set_ylabel("Median PGA at nearest receiver (g)")
    ax.set_title(
        "2020 Elazığ-Sivrice earthquake: PGA sensitivity to source depth\n"
        "2020-01-24 17:55:13 | Mww 6.7 | fixed receiver, magnitude, rake and Vs30"
    )
    ax.grid(alpha=0.25)
    ax.margins(y=0.08)
    ax.text(
        0.02,
        0.04,
        f"Nearest receiver: Repi = {repi:.1f} km, Vs30 = {vs30:.1f} m/s",
        transform=ax.transAxes,
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "0.6"},
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / "elazig_sivrice_pga_vs_depth.png", dpi=200)
    plt.close(fig)


def build_map_data(results):
    keys = [
        "location_id",
        "receiver_latitude",
        "receiver_longitude",
        "repi_km",
        "median_pga_g",
        "structural_loss_ratio_mean",
    ]

    analysed = results[results["depth_source"] == REFERENCE_SOURCE][keys].rename(
        columns={
            "median_pga_g": "analysed_pga_g",
            "structural_loss_ratio_mean": "analysed_loss_ratio",
        }
    )
    gcm_t = results[results["depth_source"] == COMPARISON_SOURCE][keys].rename(
        columns={
            "median_pga_g": "global_cmt_pga_g",
            "structural_loss_ratio_mean": "global_cmt_loss_ratio",
        }
    )

    merged = analysed.merge(
        gcm_t,
        on=["location_id", "receiver_latitude", "receiver_longitude", "repi_km"],
        how="inner",
        validate="one_to_one",
    )
    # Presentation convention: analysed (14 km) minus gCMT (12 km).
    merged["pga_difference_g"] = (
        merged["analysed_pga_g"] - merged["global_cmt_pga_g"]
    )
    merged["loss_ratio_difference"] = (
        merged["analysed_loss_ratio"] - merged["global_cmt_loss_ratio"]
    )

    if (merged["loss_ratio_difference"] > 1e-12).any():
        raise ValueError(
            "Unexpected positive analysed-minus-gCMT loss difference for the "
            "deeper analysed depth."
        )
    return merged


def plot_loss_map(map_data):
    near = map_data[map_data["repi_km"] <= MAP_MAX_REPI_KM].copy()
    if near.empty:
        raise ValueError("No Iris receivers lie within 150 km.")

    values = near["loss_ratio_difference"].to_numpy(float)
    maximum = float(np.abs(values).max())
    if maximum == 0.0:
        norm = mcolors.Normalize(vmin=-1.0, vmax=1.0)
    else:
        norm = mcolors.TwoSlopeNorm(vmin=-maximum, vcenter=0.0, vmax=maximum)

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)

    points = ax.scatter(
        near["receiver_longitude"],
        near["receiver_latitude"],
        c=values,
        cmap="RdBu",
        norm=norm,
        s=58,
        edgecolor="black",
        linewidth=0.3,
        zorder=3,
    )
    ax.scatter(
        IRIS_EVENT["longitude"],
        IRIS_EVENT["latitude"],
        marker="*",
        s=240,
        color="tab:blue",
        edgecolor="black",
        label="Earthquake",
        zorder=4,
    )

    ax.set_xlim(
        near["receiver_longitude"].min() - 0.55,
        near["receiver_longitude"].max() + 0.55,
    )
    ax.set_ylim(
        near["receiver_latitude"].min() - 0.45,
        near["receiver_latitude"].max() + 0.45,
    )
    mean_lat = float(near["receiver_latitude"].mean())
    ax.set_aspect(1.0 / np.cos(np.radians(mean_lat)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    ax.set_title(
        "2020 Elazığ-Sivrice earthquake: effect of depth on structural loss\n"
        "analysed 14 km minus gCMT 12 km, receivers within 150 km\n"
        "2020-01-24 17:55:13 | Mww 6.7 | gCMT 12 km | analysed 14 km"
    )

    strongest = near.sort_values("loss_ratio_difference", ascending=True).iloc[0]
    ax.annotate(
        "Red = gCMT predicts\nhigher structural loss",
        xy=(strongest["receiver_longitude"], strongest["receiver_latitude"]),
        xytext=(IRIS_EVENT["longitude"] - 0.9, IRIS_EVENT["latitude"] + 0.9),
        arrowprops={"arrowstyle": "->", "color": "0.15"},
        color="tab:red",
        fontsize=9,
    )

    zero_count = int(
        (near["loss_ratio_difference"].abs() <= 1e-12).sum()
    )
    zero_row = near.loc[near["loss_ratio_difference"].abs().idxmin()]
    ax.annotate(
        f"{zero_count}/{len(near)} receivers:\nzero structural-loss difference",
        xy=(zero_row["receiver_longitude"], zero_row["receiver_latitude"]),
        xytext=(IRIS_EVENT["longitude"] + 0.65, IRIS_EVENT["latitude"] + 0.45),
        arrowprops={"arrowstyle": "->", "color": "0.15"},
        fontsize=9,
    )

    ax.text(
        0.02,
        0.025,
        "Red = gCMT higher; blue = analysed higher (none in this event)",
        transform=ax.transAxes,
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.65"},
    )

    colourbar = fig.colorbar(points, ax=ax)
    colourbar.set_label(
        "Mean structural loss-ratio difference (analysed minus gCMT)"
    )

    fig.tight_layout()
    fig.savefig(
        OUTPUT_FOLDER / "elazig_sivrice_analysed_minus_gCMT_loss_difference_map.png",
        dpi=200,
    )
    plt.close(fig)


def plot_vulnerability_curve(vulnerability):
    imls = np.asarray(vulnerability.intensity_measure_levels, dtype=float)
    mean_lr = np.asarray(vulnerability.mean_loss_ratios, dtype=float)

    if len(imls) != len(mean_lr) or len(imls) == 0:
        raise ValueError("Invalid vulnerability curve arrays.")

    points = pd.DataFrame(
        {
            "pga_g": imls,
            "mean_structural_loss_ratio": mean_lr,
            "vulnerability_function_id": VULNERABILITY_FUNCTION_ID,
            "vulnerability_model_version": VULNERABILITY_MODEL_VERSION,
        }
    )
    points.to_csv(VULNERABILITY_POINTS_CSV, index=False)

    x = np.concatenate([[0.01, float(imls.min())], imls])
    y = np.concatenate([[0.0, 0.0], mean_lr])

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, y, marker="o", color="tab:blue", linewidth=2.0)
    ax.set_xscale("log")
    ax.set_xlabel("PGA (g)")
    ax.set_ylabel("Mean structural loss ratio")
    ax.set_title(
        "Structural loss function used in the model\n"
        f"GEM Global Vulnerability Model {VULNERABILITY_MODEL_VERSION} | "
        f"{VULNERABILITY_FUNCTION_ID}"
    )
    ax.grid(alpha=0.25, which="both")
    ax.set_ylim(-0.02, 1.02)

    first_iml = float(imls.min())
    ax.annotate(
        f"{first_iml:.2f} g = first vulnerability IML\n"
        "below this, the code returns loss = 0",
        xy=(first_iml, 0.0),
        xytext=(0.018, 0.18),
        arrowprops={"arrowstyle": "->", "color": "0.15"},
        fontsize=9,
    )
    ax.annotate(
        "Loss rises nonlinearly\nas PGA increases",
        xy=(0.435, 0.202391),
        xytext=(0.12, 0.42),
        arrowprops={"arrowstyle": "->", "color": "0.15"},
        fontsize=9,
    )
    ax.annotate(
        "Mean loss ratio approaches 1\nat very high PGA",
        xy=(1.282, 0.999824),
        xytext=(1.8, 0.78),
        arrowprops={"arrowstyle": "->", "color": "0.15"},
        fontsize=9,
    )

    fig.tight_layout()
    fig.savefig(VULNERABILITY_FIGURE, dpi=200)
    plt.close(fig)


def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    results, vulnerability = calculate_outputs()
    summary = summarise_by_depth(results)
    map_data = build_map_data(results)

    results.to_csv(
        OUTPUT_FOLDER / "elazig_sivrice_complete_results.csv",
        index=False,
    )
    summary.to_csv(
        OUTPUT_FOLDER / "elazig_sivrice_depth_summary.csv",
        index=False,
    )
    map_data.to_csv(
        OUTPUT_FOLDER / "elazig_sivrice_analysed_minus_gCMT_map_data.csv",
        index=False,
    )

    plot_pga_vs_depth(results)
    plot_loss_map(map_data)
    plot_vulnerability_curve(vulnerability)

    print("2020 Elazığ-Sivrice event analysis complete.")
    print("Event:", IRIS_EVENT["event_id"])
    print("Depth scenarios:", len(DEPTH_SCENARIOS))
    print("Receiver-level loss rows:", len(results))
    print("\nNearest receiver:")
    print(
        nearest_receiver_rows(results)[
            [
                "depth_label",
                "source_depth_km",
                "repi_km",
                "rhypo_km",
                "median_pga_g",
                "structural_loss_ratio_mean",
            ]
        ].to_string(index=False)
    )
    print("\nAnalysed minus gCMT loss difference range:")
    print(
        map_data["loss_ratio_difference"].min(),
        "to",
        map_data["loss_ratio_difference"].max(),
    )


if __name__ == "__main__":
    main()
