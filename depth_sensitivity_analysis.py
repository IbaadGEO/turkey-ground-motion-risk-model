from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from map_plotting import plot_turkey_border


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "outputs_gwfm" / "structural_loss_ratios.csv"
OUTPUT_FOLDER = BASE_DIR / "outputs_gwfm" / "depth_sensitivity_analysis"

BASELINE_SOURCE = "waveform"
COMPARISON_SOURCES = ("isc_ehb", "global_cmt")
ALL_REQUIRED_SOURCES = {BASELINE_SOURCE, *COMPARISON_SOURCES}

MAP_EVENT_ID = "1421"
MAP_COMPARISON_SOURCE = "global_cmt"
MAP_MAX_REPI_KM = 150.0

DISTANCE_EDGES_KM = [0.0, 25.0, 50.0, 100.0, 200.0, np.inf]
DISTANCE_LABELS = ["0-25", "25-50", "50-100", "100-200", ">200"]

LOSS_CHANGE_TOLERANCE = 1e-12
PRACTICAL_LOSS_CHANGE_THRESHOLD = 1e-6


def load_results():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            "Structural-loss results were not found. Run "
            "akkar_turkey_portfolio_gwfm.py first."
        )

    results = pd.read_csv(INPUT_FILE, dtype={"event_id": str})

    required_columns = {
        "event_id",
        "location_id",
        "depth_source",
        "source_depth_km",
        "magnitude",
        "source_latitude",
        "source_longitude",
        "receiver_latitude",
        "receiver_longitude",
        "repi_km",
        "rhypo_km",
        "median_pga_g",
        "structural_loss_ratio_mean",
    }
    missing_columns = required_columns.difference(results.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"Structural-loss results are missing columns: {missing_text}."
        )

    if results.duplicated(
        ["event_id", "location_id", "depth_source"]
    ).any():
        raise ValueError(
            "Structural-loss results contain duplicate event-location-depth rows."
        )

    return results


def build_comparison_table(results):
    baseline = results[results["depth_source"] == BASELINE_SOURCE].copy()
    if baseline.empty:
        raise ValueError("No waveform baseline rows were found.")

    if (baseline["median_pga_g"] <= 0.0).any():
        raise ValueError("Waveform PGA values must be greater than zero.")

    baseline = baseline[
        [
            "event_id",
            "location_id",
            "source_depth_km",
            "magnitude",
            "source_latitude",
            "source_longitude",
            "receiver_latitude",
            "receiver_longitude",
            "repi_km",
            "rhypo_km",
            "median_pga_g",
            "structural_loss_ratio_mean",
        ]
    ].rename(
        columns={
            "source_depth_km": "waveform_depth_km",
            "rhypo_km": "waveform_rhypo_km",
            "median_pga_g": "waveform_pga_g",
            "structural_loss_ratio_mean": "waveform_loss_ratio",
        }
    )

    comparisons = []

    for comparison_source in COMPARISON_SOURCES:
        alternative = results[
            results["depth_source"] == comparison_source
        ].copy()

        if alternative.empty:
            print(f"No {comparison_source} rows were found.")
            continue

        alternative = alternative[
            [
                "event_id",
                "location_id",
                "source_depth_km",
                "repi_km",
                "rhypo_km",
                "median_pga_g",
                "structural_loss_ratio_mean",
            ]
        ].rename(
            columns={
                "source_depth_km": "comparison_depth_km",
                "repi_km": "comparison_repi_km",
                "rhypo_km": "comparison_rhypo_km",
                "median_pga_g": "comparison_pga_g",
                "structural_loss_ratio_mean": "comparison_loss_ratio",
            }
        )

        paired = baseline.merge(
            alternative,
            on=["event_id", "location_id"],
            how="inner",
            validate="one_to_one",
        )

        if paired.empty:
            print(
                f"No paired waveform/{comparison_source} rows were found."
            )
            continue

        if not np.allclose(
            paired["repi_km"],
            paired["comparison_repi_km"],
            rtol=0.0,
            atol=1e-8,
        ):
            raise ValueError(
                "Epicentral distance changed between depth-source scenarios."
            )

        paired["comparison_source"] = comparison_source
        paired["depth_difference_km"] = (
            paired["comparison_depth_km"]
            - paired["waveform_depth_km"]
        )
        paired["rhypo_difference_km"] = (
            paired["comparison_rhypo_km"]
            - paired["waveform_rhypo_km"]
        )
        paired["pga_difference_g"] = (
            paired["comparison_pga_g"]
            - paired["waveform_pga_g"]
        )
        paired["pga_percent_change"] = (
            100.0
            * paired["pga_difference_g"]
            / paired["waveform_pga_g"]
        )
        paired["absolute_pga_percent_change"] = (
            paired["pga_percent_change"].abs()
        )
        paired["loss_ratio_difference"] = (
            paired["comparison_loss_ratio"]
            - paired["waveform_loss_ratio"]
        )
        paired["absolute_loss_ratio_difference"] = (
            paired["loss_ratio_difference"].abs()
        )
        paired["loss_changed"] = (
            paired["absolute_loss_ratio_difference"]
            > LOSS_CHANGE_TOLERANCE
        )
        paired["practical_loss_change"] = (
            paired["absolute_loss_ratio_difference"]
            >= PRACTICAL_LOSS_CHANGE_THRESHOLD
        )
        paired["depth_direction"] = np.select(
            [
                paired["depth_difference_km"] > 0.0,
                paired["depth_difference_km"] < 0.0,
            ],
            ["deeper", "shallower"],
            default="same",
        )
        paired["distance_bin_km"] = pd.cut(
            paired["repi_km"],
            bins=DISTANCE_EDGES_KM,
            labels=DISTANCE_LABELS,
            include_lowest=True,
            right=False,
        )

        comparisons.append(paired)

    if not comparisons:
        raise ValueError("No paired depth-source comparisons were created.")

    return pd.concat(comparisons, ignore_index=True)


def find_common_event_ids(results):
    source_sets = (
        results.groupby("event_id")["depth_source"]
        .agg(lambda values: set(values))
    )

    common_event_ids = [
        event_id
        for event_id, source_set in source_sets.items()
        if ALL_REQUIRED_SOURCES.issubset(source_set)
    ]

    if not common_event_ids:
        raise ValueError(
            "No earthquakes contain waveform, ISC-EHB and Global CMT depths."
        )

    return sorted(common_event_ids)


def summarise_by_distance(comparisons):
    grouped = comparisons.groupby(
        ["comparison_source", "distance_bin_km"],
        observed=False,
    )

    summary = grouped.agg(
        pair_count=("location_id", "size"),
        event_count=("event_id", "nunique"),
        median_depth_difference_km=(
            "depth_difference_km",
            "median",
        ),
        median_signed_pga_change_percent=(
            "pga_percent_change",
            "median",
        ),
        median_absolute_pga_change_percent=(
            "absolute_pga_percent_change",
            "median",
        ),
        mean_absolute_pga_change_percent=(
            "absolute_pga_percent_change",
            "mean",
        ),
        median_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            "median",
        ),
        mean_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            "mean",
        ),
        p95_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            lambda values: values.quantile(0.95),
        ),
        maximum_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            "max",
        ),
        loss_changed_percent=(
            "loss_changed",
            lambda values: 100.0 * values.mean(),
        ),
        practical_loss_change_percent=(
            "practical_loss_change",
            lambda values: 100.0 * values.mean(),
        ),
    ).reset_index()

    return summary


def summarise_depth_direction(comparisons):
    return (
        comparisons.groupby(
            ["comparison_source", "depth_direction"],
            observed=False,
        )
        .agg(
            pair_count=("location_id", "size"),
            event_count=("event_id", "nunique"),
            median_depth_difference_km=(
                "depth_difference_km",
                "median",
            ),
            median_signed_pga_change_percent=(
                "pga_percent_change",
                "median",
            ),
            mean_signed_loss_ratio_difference=(
                "loss_ratio_difference",
                "mean",
            ),
        )
        .reset_index()
    )



def summarise_depth_direction_by_distance(comparisons):
    grouped = comparisons.groupby(
        ["comparison_source", "depth_direction", "distance_bin_km"],
        observed=False,
    )

    return grouped.agg(
        pair_count=("location_id", "size"),
        event_count=("event_id", "nunique"),
        median_depth_difference_km=(
            "depth_difference_km",
            "median",
        ),
        median_signed_pga_change_percent=(
            "pga_percent_change",
            "median",
        ),
        median_absolute_pga_change_percent=(
            "absolute_pga_percent_change",
            "median",
        ),
        mean_signed_loss_ratio_difference=(
            "loss_ratio_difference",
            "mean",
        ),
        mean_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            "mean",
        ),
        p95_absolute_loss_ratio_difference=(
            "absolute_loss_ratio_difference",
            lambda values: values.quantile(0.95),
        ),
        loss_changed_percent=(
            "loss_changed",
            lambda values: 100.0 * values.mean(),
        ),
        practical_loss_change_percent=(
            "practical_loss_change",
            lambda values: 100.0 * values.mean(),
        ),
    ).reset_index()

def plot_pga_sensitivity(common_summary):
    fig, ax = plt.subplots(figsize=(10, 6))

    for comparison_source in COMPARISON_SOURCES:
        source_summary = common_summary[
            common_summary["comparison_source"] == comparison_source
        ]
        if source_summary.empty:
            continue

        ax.plot(
            source_summary["distance_bin_km"].astype(str),
            source_summary["median_absolute_pga_change_percent"],
            marker="o",
            label=f"{comparison_source} vs waveform",
        )

    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel("Median absolute PGA change (%)")
    ax.set_title(
        "PGA sensitivity to catalogue depth\n"
        "Same earthquakes available in all three catalogues"
    )
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        OUTPUT_FOLDER / "pga_sensitivity_by_distance.png",
        dpi=150,
    )
    plt.close(fig)


def plot_loss_sensitivity(common_summary):
    fig, ax = plt.subplots(figsize=(10, 6))

    for comparison_source in COMPARISON_SOURCES:
        source_summary = common_summary[
            common_summary["comparison_source"] == comparison_source
        ]
        if source_summary.empty:
            continue

        distance_labels = source_summary["distance_bin_km"].astype(str)

        ax.plot(
            distance_labels,
            source_summary["mean_absolute_loss_ratio_difference"],
            marker="o",
            label=f"{comparison_source} mean",
        )
        ax.plot(
            distance_labels,
            source_summary["p95_absolute_loss_ratio_difference"],
            marker="s",
            linestyle="--",
            label=f"{comparison_source} 95th percentile",
        )

    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel("Absolute change in mean structural loss ratio")
    ax.set_title(
        "Structural-loss sensitivity to catalogue depth\n"
        "Same earthquakes available in all three catalogues"
    )
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        OUTPUT_FOLDER / "loss_sensitivity_by_distance.png",
        dpi=150,
    )
    plt.close(fig)


def set_map_shape(ax, latitudes):
    mean_latitude = float(pd.Series(latitudes).mean())
    ax.set_aspect(1.0 / np.cos(np.radians(mean_latitude)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_axisbelow(True)
    ax.grid(alpha=0.25)


def plot_event_loss_difference_map(comparisons):
    map_results = comparisons[
        (comparisons["event_id"] == MAP_EVENT_ID)
        & (
            comparisons["comparison_source"]
            == MAP_COMPARISON_SOURCE
        )
    ].copy()

    if map_results.empty:
        print(
            f"No paired data for event {MAP_EVENT_ID} using "
            f"{MAP_COMPARISON_SOURCE}; event map was skipped."
        )
        return

    near_field = map_results[
        map_results["repi_km"] <= MAP_MAX_REPI_KM
    ].copy()

    if near_field.empty:
        print(
            f"No receivers within {MAP_MAX_REPI_KM:.0f} km for event "
            f"{MAP_EVENT_ID}; using all receivers instead."
        )
        near_field = map_results

    values = near_field["loss_ratio_difference"].to_numpy(float)
    maximum_absolute = float(np.abs(values).max())

    if maximum_absolute == 0.0:
        normalisation = mcolors.Normalize(vmin=-1.0, vmax=1.0)
    else:
        normalisation = mcolors.TwoSlopeNorm(
            vmin=-maximum_absolute,
            vcenter=0.0,
            vmax=maximum_absolute,
        )

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)

    points = ax.scatter(
        near_field["receiver_longitude"],
        near_field["receiver_latitude"],
        c=values,
        cmap="coolwarm",
        norm=normalisation,
        s=55,
        edgecolor="black",
        linewidth=0.3,
        zorder=3,
    )

    event = near_field.iloc[0]
    ax.scatter(
        event["source_longitude"],
        event["source_latitude"],
        marker="*",
        s=220,
        edgecolor="black",
        label="Earthquake",
        zorder=4,
    )

    lat_padding = 0.6
    lon_padding = 0.8
    ax.set_xlim(
        near_field["receiver_longitude"].min() - lon_padding,
        near_field["receiver_longitude"].max() + lon_padding,
    )
    ax.set_ylim(
        near_field["receiver_latitude"].min() - lat_padding,
        near_field["receiver_latitude"].max() + lat_padding,
    )

    ax.set_title(
        f"Event {MAP_EVENT_ID}: effect of catalogue depth on structural loss\n"
        f"{MAP_COMPARISON_SOURCE} minus waveform, receivers within "
        f"{MAP_MAX_REPI_KM:.0f} km"
    )
    set_map_shape(ax, near_field["receiver_latitude"])
    ax.legend()

    colorbar = fig.colorbar(points, ax=ax)
    colorbar.set_label(
        "Mean structural loss-ratio difference "
        "(comparison minus waveform)"
    )

    fig.tight_layout()
    fig.savefig(
        OUTPUT_FOLDER
        / (
            f"event_{MAP_EVENT_ID}_"
            f"{MAP_COMPARISON_SOURCE}_loss_difference_map.png"
        ),
        dpi=150,
    )
    plt.close(fig)

def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    results = load_results()
    comparisons = build_comparison_table(results)

    common_event_ids = find_common_event_ids(results)
    common_comparisons = comparisons[
        comparisons["event_id"].isin(common_event_ids)
    ].copy()

    all_available_summary = summarise_by_distance(comparisons)
    common_event_summary = summarise_by_distance(common_comparisons)
    depth_direction_summary = summarise_depth_direction(common_comparisons)
    depth_direction_distance_summary = summarise_depth_direction_by_distance(
        common_comparisons
    )

    all_available_summary.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_all_available_summary.csv",
        index=False,
    )
    common_event_summary.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_common_events_summary.csv",
        index=False,
    )
    depth_direction_summary.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_depth_direction_summary.csv",
        index=False,
    )
    depth_direction_distance_summary.to_csv(
        OUTPUT_FOLDER
        / "depth_sensitivity_depth_direction_by_distance.csv",
        index=False,
    )
    pd.DataFrame({"event_id": common_event_ids}).to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_common_event_ids.csv",
        index=False,
    )

    legacy_summary = OUTPUT_FOLDER / "depth_sensitivity_summary.csv"
    if legacy_summary.exists():
        legacy_summary.unlink()

    plot_pga_sensitivity(common_event_summary)
    plot_loss_sensitivity(common_event_summary)
    plot_event_loss_difference_map(common_comparisons)

    print("Depth-sensitivity analysis complete.")
    print("All paired rows:", len(comparisons))
    print("All events compared:", comparisons["event_id"].nunique())
    print("Common three-catalogue events:", len(common_event_ids))
    print("Common-event paired rows:", len(common_comparisons))
    print("Loss-change tolerance:", LOSS_CHANGE_TOLERANCE)
    print(
        "Practical loss-change threshold:",
        PRACTICAL_LOSS_CHANGE_THRESHOLD,
    )
    print("Saved:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
