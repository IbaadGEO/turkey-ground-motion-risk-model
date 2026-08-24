"""Compare PGA and structural loss across earthquake depth catalogues."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = (
    BASE_DIR
    / "outputs_gwfm"
    / "complete_output"
    / "earthquake_depth_pga_loss_summary.csv"
)
OUTPUT_FOLDER = BASE_DIR / "outputs_gwfm" / "depth_sensitivity_analysis"
EVENT_VALUES_FILE = OUTPUT_FOLDER / "catalogue_boxplot_event_maxima.csv"
SUMMARY_FILE = OUTPUT_FOLDER / "catalogue_boxplot_summary.csv"
FIGURE_FILE = OUTPUT_FOLDER / "catalogue_pga_loss_boxplots.png"

SOURCE_ORDER = ("waveform", "isc_ehb", "global_cmt")
SOURCE_LABELS = {
    "waveform": "gWFM",
    "isc_ehb": "ISC-EHB",
    "global_cmt": "gCMT",
}
SOURCE_COLOURS = {
    "waveform": "#3B7A57",
    "isc_ehb": "#E69F00",
    "global_cmt": "#4C78A8",
}

REQUIRED_COLUMNS = {
    "event_id",
    "depth_source",
    "maximum_pga_g",
    "maximum_structural_loss_ratio",
}


def load_event_summary(input_file=INPUT_FILE):
    """Load the one-row-per-event-and-depth summary."""
    input_file = Path(input_file)
    if not input_file.is_file():
        raise FileNotFoundError(
            "Earthquake-depth PGA/loss summary was not found. Run "
            "akkar_turkey_portfolio_gwfm.py first."
        )

    summary = pd.read_csv(input_file, dtype={"event_id": str})
    missing = REQUIRED_COLUMNS.difference(summary.columns)
    if missing:
        raise ValueError(
            "Earthquake-depth summary is missing columns: "
            + ", ".join(sorted(missing))
        )
    return summary


def prepare_common_event_values(summary):
    """Return balanced event-level maxima for the three depth catalogues."""
    summary = summary.copy()
    summary["event_id"] = summary["event_id"].astype(str)

    if summary.duplicated(["event_id", "depth_source"]).any():
        raise ValueError(
            "Earthquake-depth summary contains duplicate event/source rows."
        )

    source_sets = summary.groupby("event_id")["depth_source"].agg(set)
    required_sources = set(SOURCE_ORDER)
    common_event_ids = source_sets[
        source_sets.map(required_sources.issubset)
    ].index
    if len(common_event_ids) == 0:
        raise ValueError(
            "No earthquakes contain gWFM, ISC-EHB and gCMT depths."
        )

    values = summary[
        summary["event_id"].isin(common_event_ids)
        & summary["depth_source"].isin(SOURCE_ORDER)
    ].copy()

    expected_rows = len(common_event_ids) * len(SOURCE_ORDER)
    if len(values) != expected_rows:
        raise ValueError(
            "Common-event catalogue data are not a balanced three-source set."
        )

    numeric_columns = [
        "maximum_pga_g",
        "maximum_structural_loss_ratio",
    ]
    if not np.isfinite(values[numeric_columns].to_numpy(float)).all():
        raise ValueError("PGA and structural-loss values must be finite.")
    if (values["maximum_pga_g"] <= 0.0).any():
        raise ValueError("Maximum PGA values must be greater than zero.")
    if not values["maximum_structural_loss_ratio"].between(0.0, 1.0).all():
        raise ValueError(
            "Maximum mean structural loss ratios must be between zero and one."
        )

    source_rank = {source: rank for rank, source in enumerate(SOURCE_ORDER)}
    values["catalogue_label"] = values["depth_source"].map(SOURCE_LABELS)
    values["maximum_structural_loss_percent"] = (
        100.0 * values["maximum_structural_loss_ratio"]
    )
    values["_source_rank"] = values["depth_source"].map(source_rank)
    values = values.sort_values(["_source_rank", "event_id"]).drop(
        columns="_source_rank"
    )
    return values.reset_index(drop=True)


def summarise_catalogue_distributions(values):
    """Build the numerical summary reported alongside the figure."""
    rows = []
    for source in SOURCE_ORDER:
        source_values = values[values["depth_source"] == source]
        pga = source_values["maximum_pga_g"]
        loss = source_values["maximum_structural_loss_ratio"]
        rows.append(
            {
                "depth_source": source,
                "catalogue_label": SOURCE_LABELS[source],
                "event_count": len(source_values),
                "p25_event_maximum_pga_g": pga.quantile(0.25),
                "median_event_maximum_pga_g": pga.median(),
                "p75_event_maximum_pga_g": pga.quantile(0.75),
                "largest_event_maximum_pga_g": pga.max(),
                "zero_loss_event_count": int((loss == 0.0).sum()),
                "nonzero_loss_event_count": int((loss > 0.0).sum()),
                "p25_event_maximum_structural_loss_ratio": loss.quantile(0.25),
                "median_event_maximum_structural_loss_ratio": loss.median(),
                "p75_event_maximum_structural_loss_ratio": loss.quantile(0.75),
                "largest_event_maximum_structural_loss_ratio": loss.max(),
            }
        )
    return pd.DataFrame(rows)


def _draw_boxplots_and_points(ax, values, column):
    grouped_values = []
    for source in SOURCE_ORDER:
        source_values = values[values["depth_source"] == source]
        grouped_values.append(source_values[column].to_numpy(float))

    boxplots = ax.boxplot(
        grouped_values,
        positions=np.arange(1, len(SOURCE_ORDER) + 1),
        widths=0.48,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.8},
        whiskerprops={"color": "0.25", "linewidth": 1.2},
        capprops={"color": "0.25", "linewidth": 1.2},
    )

    for patch, source in zip(boxplots["boxes"], SOURCE_ORDER):
        patch.set_facecolor(SOURCE_COLOURS[source])
        patch.set_edgecolor("0.2")
        patch.set_alpha(0.52)

    event_ids = sorted(values["event_id"].unique())
    jitter_by_event = dict(
        zip(event_ids, np.random.default_rng(20260824).uniform(-0.16, 0.16, len(event_ids)))
    )
    for position, source in enumerate(SOURCE_ORDER, start=1):
        source_values = values[values["depth_source"] == source].copy()
        jitter = source_values["event_id"].map(jitter_by_event).to_numpy(float)
        ax.scatter(
            position + jitter,
            source_values[column],
            s=17,
            color=SOURCE_COLOURS[source],
            edgecolor="white",
            linewidth=0.25,
            alpha=0.68,
            zorder=3,
        )

    ax.set_xticks(np.arange(1, len(SOURCE_ORDER) + 1))
    ax.set_xticklabels([SOURCE_LABELS[source] for source in SOURCE_ORDER])
    ax.set_xlim(0.55, len(SOURCE_ORDER) + 0.45)
    ax.grid(axis="y", alpha=0.22)
    ax.set_axisbelow(True)


def plot_catalogue_distributions(values, output_file=FIGURE_FILE):
    """Plot event-level PGA and structural-loss distributions side by side."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    event_count = values["event_id"].nunique()
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 6.4))

    _draw_boxplots_and_points(axes[0], values, "maximum_pga_g")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Maximum site-level median PGA (g)")
    axes[0].set_title("PGA distribution")

    _draw_boxplots_and_points(
        axes[1],
        values,
        "maximum_structural_loss_percent",
    )
    axes[1].set_yscale("symlog", linthresh=1e-6, linscale=0.75, base=10)
    maximum_loss_percent = values["maximum_structural_loss_percent"].max()
    axes[1].set_ylim(-2e-7, 1.35 * maximum_loss_percent)
    axes[1].set_ylabel("Maximum mean structural loss ratio (%)")
    axes[1].set_title("Structural-loss distribution")

    zero_counts = []
    for source in SOURCE_ORDER:
        source_values = values[values["depth_source"] == source]
        zero_count = int(
            (source_values["maximum_structural_loss_ratio"] == 0.0).sum()
        )
        zero_counts.append(f"{SOURCE_LABELS[source]} {zero_count}/{event_count}")
    axes[1].text(
        0.02,
        0.98,
        "Events with an exact zero maximum:\n" + "; ".join(zero_counts),
        transform=axes[1].transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="0.25",
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.88},
    )

    fig.suptitle(
        f"Catalogue comparison across {event_count} common earthquakes",
        fontsize=15,
        fontweight="semibold",
    )
    fig.text(
        0.5,
        0.018,
        "Each dot is one earthquake (maximum across 311 receivers). "
        "Boxes show the median and interquartile range; whiskers extend to "
        "1.5 × IQR. PGA uses a log scale; loss uses a zero-preserving "
        "pseudo-log scale.",
        ha="center",
        va="bottom",
        fontsize=9,
        color="0.3",
    )
    fig.tight_layout(rect=(0.0, 0.075, 1.0, 0.94), w_pad=3.0)
    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    summary = load_event_summary()
    values = prepare_common_event_values(summary)
    distribution_summary = summarise_catalogue_distributions(values)

    output_columns = [
        "event_id",
        "depth_source",
        "catalogue_label",
        "maximum_pga_g",
        "maximum_structural_loss_ratio",
        "maximum_structural_loss_percent",
    ]
    values[output_columns].to_csv(EVENT_VALUES_FILE, index=False)
    distribution_summary.to_csv(SUMMARY_FILE, index=False)
    plot_catalogue_distributions(values)

    print("Catalogue distribution comparison complete.")
    print("Common earthquakes:", values["event_id"].nunique())
    print("Saved:", FIGURE_FILE)
    print("Saved:", EVENT_VALUES_FILE)
    print("Saved:", SUMMARY_FILE)


if __name__ == "__main__":
    main()
