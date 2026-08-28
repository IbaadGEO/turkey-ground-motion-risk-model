from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from map_plotting import plot_turkey_border


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = (
    BASE_DIR / "outputs_gwfm" / "complete_pga_structural_loss_table.csv"
)
OUTPUT_FOLDER = BASE_DIR / "outputs_gwfm" / "depth_sensitivity_analysis"

BASELINE_SOURCE = "waveform"
COMPARISON_SOURCES = ("isc_ehb", "global_cmt")
ALL_REQUIRED_SOURCES = {BASELINE_SOURCE, *COMPARISON_SOURCES}

PLOT_SOURCE_ORDER = ("global_cmt", "isc_ehb")
SOURCE_LABELS = {
    "global_cmt": "gCMT",
    "isc_ehb": "ISC-EHB",
}
SOURCE_COLOURS = {
    "global_cmt": "tab:blue",
    "isc_ehb": "tab:orange",
}

MAP_EVENT_ID = "1421"
MAP_COMPARISON_SOURCE = "global_cmt"
MAP_MAX_REPI_KM = 150.0

DISTANCE_EDGES_KM = [0.0, 25.0, 50.0, 100.0, 200.0, np.inf]
DISTANCE_LABELS = ["0-25", "25-50", "50-100", "100-200", ">200"]

LOSS_CHANGE_TOLERANCE = 1e-12
PRACTICAL_LOSS_CHANGE_THRESHOLD = 1e-6

PRESENTATION_MAX_DISTANCE_KM = 200.0
CONTINUOUS_DISTANCE_STEP_KM = 1.0
KERNEL_BANDWIDTH_KM = 15.0
PGA_CHANGE_TOLERANCE_PERCENT = 1e-9


def load_results():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            "Complete PGA/loss results were not found. Run "
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


def _weighted_mean_and_standard_deviation(values, weights):
    """Return a kernel-weighted mean and empirical standard deviation."""

    weight_sum = float(weights.sum())
    if weight_sum <= 0.0:
        return np.nan, np.nan

    mean = float(np.average(values, weights=weights))
    variance = float(np.average((values - mean) ** 2, weights=weights))
    return mean, np.sqrt(variance)


def build_continuous_sensitivity_summary(common_comparisons):
    """Smooth raw signed pairs without reducing them to distance bins.

    A Gaussian kernel gives nearby pairs more influence at each plotted
    distance. The weighted mean is the systematic signed tendency. The
    weighted standard deviation is descriptive pair-to-pair variability; it
    is not a confidence interval or a simulated ground-motion uncertainty.
    """

    distance_grid = np.arange(
        0.0,
        PRESENTATION_MAX_DISTANCE_KM + CONTINUOUS_DISTANCE_STEP_KM,
        CONTINUOUS_DISTANCE_STEP_KM,
    )
    metric_settings = (
        ("pga_percent_change", "pga_percent", PGA_CHANGE_TOLERANCE_PERCENT),
        ("loss_ratio_difference", "loss_ratio", LOSS_CHANGE_TOLERANCE),
    )
    rows = []

    for source in PLOT_SOURCE_ORDER:
        source_rows = common_comparisons[
            (common_comparisons["comparison_source"] == source)
            & (
                common_comparisons["repi_km"]
                <= PRESENTATION_MAX_DISTANCE_KM
            )
        ]
        if source_rows.empty:
            continue

        distances = source_rows["repi_km"].to_numpy(float)

        for value_column, metric, tolerance in metric_settings:
            values = source_rows[value_column].to_numpy(float)

            for distance in distance_grid:
                offsets = (distances - distance) / KERNEL_BANDWIDTH_KM
                weights = np.exp(-0.5 * offsets ** 2)
                mean, standard_deviation = (
                    _weighted_mean_and_standard_deviation(values, weights)
                )
                effective_pair_count = float(
                    weights.sum() ** 2 / np.square(weights).sum()
                )
                weight_sum = float(weights.sum())

                rows.append(
                    {
                        "comparison_source": source,
                        "metric": metric,
                        "epicentral_distance_km": distance,
                        "kernel_bandwidth_km": KERNEL_BANDWIDTH_KM,
                        "pairs_within_200_km": len(source_rows),
                        "effective_pair_count": effective_pair_count,
                        "systematic_mean_signed_change": mean,
                        "empirical_standard_deviation": standard_deviation,
                        "weighted_negative_percent": (
                            100.0
                            * weights[values < -tolerance].sum()
                            / weight_sum
                        ),
                        "weighted_unchanged_percent": (
                            100.0
                            * weights[np.abs(values) <= tolerance].sum()
                            / weight_sum
                        ),
                        "weighted_positive_percent": (
                            100.0
                            * weights[values > tolerance].sum()
                            / weight_sum
                        ),
                    }
                )

    if not rows:
        raise ValueError("No common-event pairs were available within 200 km.")

    return pd.DataFrame(rows)


def summarise_sign_balance(common_comparisons):
    """Count lower, unchanged and higher responses in key distance ranges."""

    metric_settings = (
        ("pga_percent_change", "pga_percent", PGA_CHANGE_TOLERANCE_PERCENT),
        ("loss_ratio_difference", "loss_ratio", LOSS_CHANGE_TOLERANCE),
    )
    rows = []

    ranges = (
        ("0-25", 25.0),
        ("0-200", PRESENTATION_MAX_DISTANCE_KM),
    )

    for distance_range, maximum_distance in ranges:
        within_range = common_comparisons[
            common_comparisons["repi_km"] <= maximum_distance
        ]

        for source in PLOT_SOURCE_ORDER:
            source_rows = within_range[
                within_range["comparison_source"] == source
            ]
            for value_column, metric, tolerance in metric_settings:
                values = source_rows[value_column].to_numpy(float)
                negative_count = int((values < -tolerance).sum())
                unchanged_count = int((np.abs(values) <= tolerance).sum())
                positive_count = int((values > tolerance).sum())
                pair_count = len(values)
                if pair_count == 0:
                    continue

                rows.append(
                    {
                        "distance_range_km": distance_range,
                        "comparison_source": source,
                        "metric": metric,
                        "pair_count": pair_count,
                        "negative_count": negative_count,
                        "negative_percent": (
                            100.0 * negative_count / pair_count
                        ),
                        "unchanged_count": unchanged_count,
                        "unchanged_percent": (
                            100.0 * unchanged_count / pair_count
                        ),
                        "positive_count": positive_count,
                        "positive_percent": (
                            100.0 * positive_count / pair_count
                        ),
                    }
                )

    return pd.DataFrame(rows)


def _add_sign_balance_text(fig, sign_balance, metric):
    metric_rows = sign_balance[
        (sign_balance["metric"] == metric)
        & (sign_balance["distance_range_km"] == "0-25")
    ]
    text_parts = []

    for source in PLOT_SOURCE_ORDER:
        row = metric_rows[
            metric_rows["comparison_source"] == source
        ].iloc[0]
        text_parts.append(
            f"{SOURCE_LABELS[source]} (n={int(row['pair_count']):,}): "
            f"{row['negative_percent']:.1f}% lower  |  "
            f"{row['unchanged_percent']:.1f}% unchanged  |  "
            f"{row['positive_percent']:.1f}% higher"
        )

    fig.text(
        0.5,
        0.095,
        "Near-field sign balance (0-25 km)\n" + "\n".join(text_parts),
        ha="center",
        va="center",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.45", "fc": "white", "ec": "0.7"},
    )


def _plot_signed_sensitivity(
    common_comparisons,
    continuous_summary,
    sign_balance,
    *,
    value_column,
    metric,
    scale,
    filename,
    title,
    direction_text,
    ylabel,
):
    fig, ax = plt.subplots(figsize=(11, 7))
    in_range = common_comparisons[
        common_comparisons["repi_km"] <= PRESENTATION_MAX_DISTANCE_KM
    ]

    for source in PLOT_SOURCE_ORDER:
        colour = SOURCE_COLOURS[source]
        raw = in_range[in_range["comparison_source"] == source]
        smooth = continuous_summary[
            (continuous_summary["comparison_source"] == source)
            & (continuous_summary["metric"] == metric)
        ]

        x = smooth["epicentral_distance_km"].to_numpy(float)
        mean = (
            smooth["systematic_mean_signed_change"].to_numpy(float) * scale
        )
        spread = (
            smooth["empirical_standard_deviation"].to_numpy(float) * scale
        )

        ax.scatter(
            raw["repi_km"],
            raw[value_column] * scale,
            s=12,
            alpha=0.16,
            color=colour,
            edgecolors="none",
        )
        ax.fill_between(
            x,
            mean - spread,
            mean + spread,
            color=colour,
            alpha=0.14,
            linewidth=0.0,
        )
        ax.plot(
            x,
            mean,
            color=colour,
            linewidth=2.5,
            label=f"{SOURCE_LABELS[source]} systematic tendency",
        )

    ax.axhline(0.0, color="0.15", linewidth=1.1, zorder=1)
    ax.set_xlim(0.0, PRESENTATION_MAX_DISTANCE_KM)
    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title}\n{direction_text}")
    ax.grid(alpha=0.22)
    ax.legend(loc="best")

    _add_sign_balance_text(fig, sign_balance, metric)
    fig.text(
        0.5,
        0.018,
        "Dots: event-receiver pairs. Line: 15 km Gaussian-weighted mean "
        "(systematic signed tendency). Shading: ±1 weighted SD.\n"
        "The shading is observed pair-to-pair variability; no random "
        "ground-motion uncertainty was sampled.",
        ha="center",
        va="bottom",
        fontsize=8.0,
        color="0.3",
    )
    fig.tight_layout(rect=(0.0, 0.18, 1.0, 1.0))
    fig.savefig(OUTPUT_FOLDER / filename, dpi=200)
    plt.close(fig)


def plot_pga_sensitivity(
    common_comparisons,
    continuous_summary=None,
    sign_balance=None,
):
    if continuous_summary is None:
        continuous_summary = build_continuous_sensitivity_summary(
            common_comparisons
        )
    if sign_balance is None:
        sign_balance = summarise_sign_balance(common_comparisons)

    _plot_signed_sensitivity(
        common_comparisons,
        continuous_summary,
        sign_balance,
        value_column="pga_percent_change",
        metric="pga_percent",
        scale=1.0,
        filename="pga_sensitivity_by_distance.png",
        title="Signed PGA sensitivity to catalogue depth",
        direction_text=(
            "Comparison catalogue minus gWFM: positive = higher PGA; "
            "negative = lower PGA"
        ),
        ylabel="Signed PGA change relative to gWFM (%)",
    )


def plot_loss_sensitivity(
    common_comparisons,
    continuous_summary=None,
    sign_balance=None,
):
    if continuous_summary is None:
        continuous_summary = build_continuous_sensitivity_summary(
            common_comparisons
        )
    if sign_balance is None:
        sign_balance = summarise_sign_balance(common_comparisons)

    _plot_signed_sensitivity(
        common_comparisons,
        continuous_summary,
        sign_balance,
        value_column="loss_ratio_difference",
        metric="loss_ratio",
        scale=100.0,
        filename="loss_sensitivity_by_distance.png",
        title="Signed structural-loss sensitivity to catalogue depth",
        direction_text=(
            "Comparison catalogue minus gWFM: positive = higher loss; "
            "negative = lower loss"
        ),
        ylabel="Signed structural loss-ratio change (percentage points)",
    )


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
    continuous_summary = build_continuous_sensitivity_summary(
        common_comparisons
    )
    sign_balance = summarise_sign_balance(common_comparisons)

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
    continuous_summary.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_continuous_summary.csv",
        index=False,
    )
    sign_balance.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_sign_balance.csv",
        index=False,
    )

    legacy_summary = OUTPUT_FOLDER / "depth_sensitivity_summary.csv"
    if legacy_summary.exists():
        legacy_summary.unlink()

    plot_pga_sensitivity(
        common_comparisons,
        continuous_summary,
        sign_balance,
    )
    plot_loss_sensitivity(
        common_comparisons,
        continuous_summary,
        sign_balance,
    )
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
