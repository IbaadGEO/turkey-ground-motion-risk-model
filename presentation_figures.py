"""Generate presentation-ready depth-sensitivity figures without changing the numerical analysis."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FOLDER = BASE_DIR / "outputs_gwfm" / "depth_sensitivity_analysis"
SUMMARY_FILE = OUTPUT_FOLDER / "depth_sensitivity_common_events_summary.csv"

DISTANCE_LABELS = ["0-25", "25-50", "50-100", "100-200", ">200"]
SOURCE_LABELS = {
    "global_cmt": "gCMT",
    "isc_ehb": "ISC-EHB",
}
SOURCE_COLOURS = {
    "global_cmt": "tab:blue",
    "isc_ehb": "tab:orange",
}


def load_summary():
    summary = pd.read_csv(SUMMARY_FILE)
    required = {
        "comparison_source",
        "distance_bin_km",
        "pair_count",
        "median_absolute_pga_change_percent",
        "mean_absolute_loss_ratio_difference",
        "p95_absolute_loss_ratio_difference",
    }
    missing = required.difference(summary.columns)
    if missing:
        raise ValueError(
            "Depth-sensitivity summary is missing columns: "
            + ", ".join(sorted(missing))
        )
    return summary


def source_rows(summary, source):
    rows = summary[summary["comparison_source"] == source].copy()
    rows["distance_bin_km"] = pd.Categorical(
        rows["distance_bin_km"].astype(str),
        categories=DISTANCE_LABELS,
        ordered=True,
    )
    return rows.sort_values("distance_bin_km")


def pair_counts(summary):
    counts = []
    for label in DISTANCE_LABELS:
        rows = summary[summary["distance_bin_km"].astype(str) == label]
        if rows.empty:
            counts.append(0)
        else:
            counts.append(int(rows["pair_count"].max()))
    return counts


def add_sample_sizes(ax, summary):
    for x, count in enumerate(pair_counts(summary)):
        ax.text(
            x,
            -0.12,
            f"n = {count}",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=9,
            color="0.35",
            style="italic",
        )


def plot_pga(summary):
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(DISTANCE_LABELS))

    for source in ("global_cmt", "isc_ehb"):
        rows = source_rows(summary, source)
        values = rows["median_absolute_pga_change_percent"].to_numpy(float)
        colour = SOURCE_COLOURS[source]

        ax.plot(
            x,
            values,
            marker="o",
            linewidth=2.0,
            color=colour,
            label=f"{SOURCE_LABELS[source]} vs gWFM",
        )

        label_offset = 8 if source == "global_cmt" else -12
        label_va = "bottom" if source == "global_cmt" else "top"

        for x_value, y_value in zip(x, values):
            ax.annotate(
                f"{y_value:.1f}",
                (x_value, y_value),
                xytext=(0, label_offset),
                textcoords="offset points",
                ha="center",
                va=label_va,
                fontsize=9,
                color=colour,
            )

    ax.annotate(
        "Depth changes matter most\nclose to the source",
        xy=(0, 26.3),
        xytext=(0.55, 23.5),
        arrowprops={"arrowstyle": "->", "color": "0.25"},
        fontsize=10,
    )
    ax.annotate(
        "Sensitivity decreases\nrapidly with distance",
        xy=(2.6, 5.8),
        xytext=(2.0, 11.5),
        arrowprops={"arrowstyle": "->", "color": "0.25"},
        fontsize=10,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(DISTANCE_LABELS)
    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel("Median absolute PGA change (%)")
    ax.set_title(
        "PGA sensitivity to catalogue depth\n"
        "Same earthquakes available in all three catalogues"
    )
    ax.grid(alpha=0.25)
    ax.legend()
    ax.set_ylim(bottom=-1.0)
    add_sample_sizes(ax, summary)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18)
    fig.savefig(OUTPUT_FOLDER / "pga_sensitivity_by_distance.png", dpi=200)
    plt.close(fig)


def plot_loss(summary):
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(DISTANCE_LABELS))

    for source in ("global_cmt", "isc_ehb"):
        rows = source_rows(summary, source)
        means = rows["mean_absolute_loss_ratio_difference"].to_numpy(float)
        p95 = rows["p95_absolute_loss_ratio_difference"].to_numpy(float)
        colour = SOURCE_COLOURS[source]

        ax.plot(
            x,
            means,
            marker="o",
            linewidth=2.0,
            color=colour,
            label=f"{SOURCE_LABELS[source]} mean",
        )
        ax.plot(
            x,
            p95,
            marker="s",
            linestyle="--",
            linewidth=1.8,
            color=colour,
            label=f"{SOURCE_LABELS[source]} 95th percentile",
        )

        ax.annotate(
            f"{means[0]:.6f}",
            (0, means[0]),
            xytext=(-8, 6),
            textcoords="offset points",
            ha="right",
            fontsize=9,
            color=colour,
        )
        ax.annotate(
            f"{p95[0]:.5f}",
            (0, p95[0]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=colour,
        )

    ax.annotate(
        "Largest loss sensitivity\nis within 25 km",
        xy=(0, 0.0175),
        xytext=(0.75, 0.015),
        arrowprops={"arrowstyle": "->", "color": "0.25"},
        fontsize=10,
    )
    ax.annotate(
        "Beyond 25 km, many sites fall\n"
        "below the first vulnerability IML (0.05 g)",
        xy=(1.2, 0.00001),
        xytext=(1.75, 0.0045),
        arrowprops={"arrowstyle": "->", "color": "0.25"},
        fontsize=9,
        ha="center",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(DISTANCE_LABELS)
    ax.set_xlabel("Epicentral distance (km)")
    ax.set_ylabel("Absolute change in mean structural loss ratio")
    ax.set_title(
        "Structural-loss sensitivity to catalogue depth\n"
        "Same earthquakes available in all three catalogues"
    )
    ax.grid(alpha=0.25)
    ax.legend()
    ax.set_ylim(bottom=-0.0005)
    add_sample_sizes(ax, summary)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18)
    fig.savefig(OUTPUT_FOLDER / "loss_sensitivity_by_distance.png", dpi=200)
    plt.close(fig)


def main():
    summary = load_summary()
    plot_pga(summary)
    plot_loss(summary)

    legacy_map = OUTPUT_FOLDER / "event_1421_global_cmt_loss_difference_map.png"
    if legacy_map.exists():
        legacy_map.unlink()

    print("Presentation depth-sensitivity figures regenerated.")
    print("Catalogue colours: gCMT = blue; ISC-EHB = orange.")
    print("Removed old Event 1421 map if present.")


if __name__ == "__main__":
    main()
