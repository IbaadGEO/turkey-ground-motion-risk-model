"""Regenerate the signed, presentation-ready depth-sensitivity figures."""

from depth_sensitivity_analysis import (
    OUTPUT_FOLDER,
    build_comparison_table,
    build_continuous_sensitivity_summary,
    find_common_event_ids,
    load_results,
    plot_loss_sensitivity_presentation,
    plot_pga_sensitivity_presentation,
    summarise_sign_balance,
)


def main():
    results = load_results()
    comparisons = build_comparison_table(results)
    common_event_ids = find_common_event_ids(results)
    common_comparisons = comparisons[
        comparisons["event_id"].isin(common_event_ids)
    ].copy()

    continuous_summary = build_continuous_sensitivity_summary(
        common_comparisons
    )
    sign_balance = summarise_sign_balance(common_comparisons)

    continuous_summary.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_continuous_summary.csv",
        index=False,
    )
    sign_balance.to_csv(
        OUTPUT_FOLDER / "depth_sensitivity_sign_balance.csv",
        index=False,
    )

    pga_plot = plot_pga_sensitivity_presentation(
        common_comparisons,
        continuous_summary,
        sign_balance,
    )
    loss_plot = plot_loss_sensitivity_presentation(
        common_comparisons,
        continuous_summary,
        sign_balance,
    )

    pair_count = int(sign_balance["pair_count"].max())
    print("Signed presentation depth-sensitivity figures regenerated.")
    print("Common three-catalogue events:", len(common_event_ids))
    print("Paired rows within 200 km per comparison source:", pair_count)
    print("Catalogue colours: gCMT = blue; ISC-EHB = orange.")
    print("PGA presentation files:")
    for output_file in pga_plot["output_files"]:
        print(" ", output_file)
    print("Structural-loss presentation files:")
    for output_file in loss_plot["output_files"]:
        print(" ", output_file)
    print(
        "Structural-loss display clipping:",
        loss_plot["clipped_below_count"],
        "below and",
        loss_plot["clipped_above_count"],
        "above the y-range.",
    )


if __name__ == "__main__":
    main()
