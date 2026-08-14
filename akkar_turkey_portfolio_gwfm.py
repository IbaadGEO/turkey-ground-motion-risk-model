from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from openquake.hazardlib.gsim.akkar_2014 import AkkarEtAlRhyp2014
from openquake.hazardlib.imt import PGA, PGV, SA

from map_plotting import (
    plot_pga_receiver_points,
    plot_turkey_border,
    plot_vs30_map,
)
from prepare_gwfm_catalogue import (
    build_event_depth_table,
    print_distance_summary,
    select_gwfm_events,
)
from vulnerability import (
    calculate_structural_loss_ratios,
    load_structural_vulnerability_curve,
)


# Input and output files
CATALOGUE_FILE = Path("data/gwfm_v1_2_clean.csv")
EVENT_SELECTION_FILE = Path("data/gwfm_117_event_selection.csv")
SELECTION_ID_COLUMN = "event_id"
EXPOSURE_FILE = Path("data/turkey_50km_land_grid_vs30.csv")
VULNERABILITY_FILE = Path(
    "data/gem_vulnerability_v2026/vulnerability_structural.xml"
)
OUTPUT_FOLDER = Path("outputs_gwfm")

# Calculation settings
MAP_EVENT_ID = "1421"
MAP_DEPTH_SOURCE = "waveform"
RUN_BENCHMARK = True
AKKAR_MAX_DEPTH_KM = 30.0
EXPECTED_EARTHQUAKES = 117
EXPECTED_EXPOSURE_LOCATIONS = 311
EXPECTED_VALID_DEPTHS = {
    "waveform": 117,
    "isc_ehb": 110,
    "global_cmt": 94,
}
VULNERABILITY_FUNCTION_ID = "MUR+CLBRS/LWAL/CDN+ERN/H:1/RES"
VULNERABILITY_MODEL_VERSION = "v2026.0.0"
VULNERABILITY_MODEL_SHA256 = (
    "ABAAD2CBD313780E370DC1DD97DB01061FB03E58D5FA5C7590B2A879019F6116"
)


def run_benchmark():
    repi_km = 10.2729
    depths_km = np.array([8.0, 15.0])
    rhypo_km = np.hypot(repi_km, depths_km)

    context = np.rec.fromarrays(
        [
            np.array([6.0, 6.0]),
            np.array([0.0, 0.0]),
            np.array([760.0, 760.0]),
            rhypo_km,
        ],
        names=["mag", "rake", "vs30", "rhypo"],
    )

    mean = np.zeros((1, 2))
    sigma = np.zeros((1, 2))
    tau = np.zeros((1, 2))
    phi = np.zeros((1, 2))

    gmpe = AkkarEtAlRhyp2014()
    gmpe.compute(context, [PGA()], mean, sigma, tau, phi)

    calculated_pga = np.exp(mean[0])
    expected_pga = np.array([0.2090, 0.1333])

    if not np.allclose(calculated_pga, expected_pga, rtol=0.005, atol=0.0005):
        raise ValueError("The benchmark results do not match the expected values.")

    print("Benchmark passed:", calculated_pga.round(4).tolist(), "g")


def load_inputs():
    catalogue = pd.read_csv(
        CATALOGUE_FILE,
        dtype={"event_id": str},
        parse_dates=["origin_time"],
    )
    earthquakes = select_gwfm_events(
        catalogue,
        EVENT_SELECTION_FILE,
        SELECTION_ID_COLUMN,
    )
    event_depths = build_event_depth_table(earthquakes)

    exposure = pd.read_csv(EXPOSURE_FILE)
    exposure = exposure[
        ["location_id", "latitude", "longitude", "vs30_m_s", "vs30_status"]
    ].copy()
    exposure = exposure.rename(columns={"vs30_m_s": "vs30"})

    vulnerability = load_structural_vulnerability_curve(
        VULNERABILITY_FILE,
        VULNERABILITY_FUNCTION_ID,
        VULNERABILITY_MODEL_SHA256,
    )

    if len(earthquakes) != EXPECTED_EARTHQUAKES:
        raise ValueError(
            f"Expected {EXPECTED_EARTHQUAKES} earthquakes, "
            f"but loaded {len(earthquakes)}."
        )

    if len(exposure) != EXPECTED_EXPOSURE_LOCATIONS:
        raise ValueError(
            f"Expected {EXPECTED_EXPOSURE_LOCATIONS} exposure locations, "
            f"but loaded {len(exposure)}."
        )

    if not np.isfinite(exposure["vs30"]).all():
        raise ValueError("Every exposure location must have a finite Vs30 value.")
    if not exposure["vs30"].between(150.0, 1200.0, inclusive="neither").all():
        raise ValueError("Vs30 values must be between 150 and 1200 m/s.")
    if not exposure["vs30_status"].isin(["direct", "nearest_valid"]).all():
        raise ValueError("Every exposure location must have a completed Vs30 status.")

    valid_depths = event_depths[event_depths["depth_status"] == "valid"]
    valid_depth_counts = valid_depths["depth_source"].value_counts()
    for depth_source, expected_count in EXPECTED_VALID_DEPTHS.items():
        actual_count = int(valid_depth_counts.get(depth_source, 0))
        if actual_count != expected_count:
            raise ValueError(
                f"Expected {expected_count} valid {depth_source} depths, "
                f"but found {actual_count}."
            )

    deep_depths = valid_depths["depth_km"] > AKKAR_MAX_DEPTH_KM

    print("Valid depths at or below 30 km:", int((~deep_depths).sum()))
    print("Valid depths deeper than 30 km:", int(deep_depths.sum()))

    if deep_depths.any():
        print(
            "WARNING: Akkar et al. (2014) states the model is intended "
            "for focal depths not greater than 30 km. Deeper events are "
            "retained for now pending guidance."
        )

    print("Earthquakes loaded:", len(earthquakes))
    print("Event-depth rows created:", len(event_depths))
    print("Exposure locations loaded:", len(exposure))
    print("Vs30 values sampled directly:", int((exposure["vs30_status"] == "direct").sum()))
    print(
        "Vs30 values filled from nearest valid cell:",
        int((exposure["vs30_status"] == "nearest_valid").sum()),
    )
    print(
        "Vs30 range:",
        round(exposure["vs30"].min(), 1),
        "to",
        round(exposure["vs30"].max(), 1),
        "m/s",
    )
    print(
        "Structural loss ratios use GEM Global Vulnerability Model",
        VULNERABILITY_MODEL_VERSION,
        "function",
        VULNERABILITY_FUNCTION_ID,
    )
    print("Contents, nonstructural and fatalities models are excluded.")

    return earthquakes, event_depths, exposure, vulnerability


def haversine_distance_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0088

    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)

    a = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat1_rad)
        * np.cos(lat2_rad)
        * np.sin(delta_lon / 2.0) ** 2
    )

    return 2.0 * earth_radius_km * np.arcsin(np.sqrt(a))


def create_source_receiver_pairs(earthquakes, event_depths, exposure):
    rows = []
    valid_depths = event_depths[event_depths["depth_status"] == "valid"]

    for _, earthquake in earthquakes.iterrows():
        earthquake_depths = valid_depths[
            valid_depths["event_id"] == earthquake["event_id"]
        ]

        for _, depth in earthquake_depths.iterrows():
            for _, location in exposure.iterrows():
                repi_km = haversine_distance_km(
                    earthquake["latitude"],
                    earthquake["longitude"],
                    location["latitude"],
                    location["longitude"],
                )
                rhypo_km = np.hypot(repi_km, depth["depth_km"])

                rows.append(
                    {
                        "event_id": earthquake["event_id"],
                        "origin_time": earthquake["origin_time"],
                        "magnitude": earthquake["magnitude"],
                        "magnitude_type": earthquake["magnitude_type"],
                        "rake": earthquake["rake"],
                        "source_latitude": earthquake["latitude"],
                        "source_longitude": earthquake["longitude"],
                        "depth_source": depth["depth_source"],
                        "source_depth_km": depth["depth_km"],
                        "location_id": location["location_id"],
                        "receiver_latitude": location["latitude"],
                        "receiver_longitude": location["longitude"],
                        "vs30": location["vs30"],
                        "repi_km": repi_km,
                        "rhypo_km": rhypo_km,
                        "source_within_30_km": (
                            depth["depth_km"] <= AKKAR_MAX_DEPTH_KM
                        ),
                        "within_200_km": rhypo_km <= 200.0,
                    }
                )

    scenarios = pd.DataFrame(rows)
    print("Source-receiver pairs created:", len(scenarios))
    print("Pairs by depth source:")
    print(scenarios["depth_source"].value_counts().to_string())
    print_distance_summary(scenarios)
    return scenarios


def calculate_ground_motion(scenarios):
    imts = [
        ("PGA", PGA(), "g"),
        ("PGV", PGV(), "cm/s"),
        ("SA(0.2 s)", SA(0.2), "g"),
        ("SA(1 s)", SA(1.0), "g"),
    ]

    context = np.rec.fromarrays(
        [
            scenarios["magnitude"].to_numpy(float),
            scenarios["rake"].to_numpy(float),
            scenarios["vs30"].to_numpy(float),
            scenarios["rhypo_km"].to_numpy(float),
        ],
        names=["mag", "rake", "vs30", "rhypo"],
    )

    output_shape = (len(imts), len(scenarios))
    mean = np.zeros(output_shape)
    sigma = np.zeros(output_shape)
    tau = np.zeros(output_shape)
    phi = np.zeros(output_shape)

    gmpe = AkkarEtAlRhyp2014()
    gmpe.compute(
        context,
        [imt[1] for imt in imts],
        mean,
        sigma,
        tau,
        phi,
    )

    median_values = np.exp(mean)
    result_tables = []

    for imt_number, (label, _, unit) in enumerate(imts):
        imt_results = scenarios.copy()
        imt_results["imt"] = label
        imt_results["unit"] = unit
        imt_results["median_value"] = median_values[imt_number]
        imt_results["sigma_total_ln"] = sigma[imt_number]
        result_tables.append(imt_results)

    results = pd.concat(result_tables, ignore_index=True)
    print("Ground-motion rows calculated:", len(results))
    return results


def calculate_structural_loss(results, vulnerability):
    structural_loss = calculate_structural_loss_ratios(
        results,
        vulnerability,
        VULNERABILITY_MODEL_VERSION,
    )

    print("Structural-loss-ratio rows calculated:", len(structural_loss))
    return structural_loss


def set_map_shape(ax, latitudes):
    mean_latitude = float(pd.Series(latitudes).mean())
    ax.set_aspect(1.0 / np.cos(np.radians(mean_latitude)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_axisbelow(True)
    ax.grid(alpha=0.25)


def plot_inputs(earthquakes, exposure):
    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)

    ax.scatter(
        exposure["longitude"],
        exposure["latitude"],
        s=15,
        color="steelblue",
        label="Exposure locations",
        zorder=3,
    )
    ax.scatter(
        earthquakes["longitude"],
        earthquakes["latitude"],
        s=70,
        marker="*",
        color="darkorange",
        edgecolor="black",
        linewidth=0.4,
        label="gWFM earthquakes",
        zorder=4,
    )

    ax.set_title("Exposure grid and selected gWFM earthquakes")
    set_map_shape(ax, exposure["latitude"])
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / "exposure_and_earthquakes.png", dpi=150)
    plt.close(fig)


def plot_pga_map(structural_loss):
    map_results = structural_loss[
        (structural_loss["event_id"] == MAP_EVENT_ID)
        & (structural_loss["depth_source"] == MAP_DEPTH_SOURCE)
    ].copy()

    if map_results.empty:
        selected_depth_results = structural_loss[
            structural_loss["depth_source"] == MAP_DEPTH_SOURCE
        ]
        largest_event = selected_depth_results.sort_values(
            "magnitude", ascending=False
        ).iloc[0]
        map_results = structural_loss[
            (structural_loss["event_id"] == largest_event["event_id"])
            & (structural_loss["depth_source"] == MAP_DEPTH_SOURCE)
        ].copy()

    event = map_results.iloc[0]
    event_id = event["event_id"]

    fig, ax = plt.subplots(figsize=(11, 6))
    plot_turkey_border(ax)
    points = plot_pga_receiver_points(ax, map_results)
    ax.scatter(
        event["source_longitude"],
        event["source_latitude"],
        s=180,
        marker="*",
        color="darkorange",
        edgecolor="black",
        label="Earthquake",
        zorder=4,
    )

    ax.set_title(
        f"Median PGA for gWFM event {event_id}\n"
        f"Mw {event['magnitude']:.2f}, {event['depth_source']} depth "
        f"{event['source_depth_km']:.1f} km"
    )
    set_map_shape(ax, map_results["receiver_latitude"])
    ax.legend()
    if points is not None:
        colorbar = fig.colorbar(points, ax=ax)
        colorbar_label = "Median PGA (g)"
        if isinstance(points.norm, matplotlib.colors.LogNorm):
            colorbar_label += ", logarithmic colour scale"
        colorbar.set_label(colorbar_label)
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / f"pga_map_{event_id}.png", dpi=150)
    plt.close(fig)


def main():
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    if RUN_BENCHMARK:
        run_benchmark()

    earthquakes, event_depths, exposure, vulnerability = load_inputs()
    scenarios = create_source_receiver_pairs(
        earthquakes,
        event_depths,
        exposure,
    )
    results = calculate_ground_motion(scenarios)
    structural_loss = calculate_structural_loss(results, vulnerability)

    results.to_csv(OUTPUT_FOLDER / "ground_motion_results.csv", index=False)
    structural_loss.to_csv(
        OUTPUT_FOLDER / "structural_loss_ratios.csv",
        index=False,
    )
    event_depths.to_csv(
        OUTPUT_FOLDER / "selected_event_depths.csv",
        index=False,
    )

    plot_inputs(earthquakes, exposure)
    plot_pga_map(structural_loss)
    plot_vs30_map(exposure, OUTPUT_FOLDER / "vs30_map.png", "vs30")

    print("Finished. Results were saved in:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
