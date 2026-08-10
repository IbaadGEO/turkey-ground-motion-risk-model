from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from openquake.hazardlib.gsim.akkar_2014 import AkkarEtAlRhyp2014
from openquake.hazardlib.imt import PGA, PGV, SA

from prepare_gwfm_catalogue import (
    print_distance_summary,
    select_gwfm_events,
    validate_vulnerability_curve,
)


# Input and output files
CATALOGUE_FILE = Path("data/gwfm_v1_2_clean.csv")
EVENT_SELECTION_FILE = Path("data/gwfm_117_event_selection.csv")
SELECTION_ID_COLUMN = "event_id"
EXPOSURE_FILE = Path("data/turkey_50km_land_grid.csv")
VULNERABILITY_FILE = Path("data/provisional_vulnerability_curve.csv")
OUTPUT_FOLDER = Path("outputs_gwfm")

# Calculation settings
VS30 = 760.0
MAP_EVENT_ID = "1421"
RUN_BENCHMARK = True
AKKAR_MAX_DEPTH_KM = 30.0
EXPECTED_EARTHQUAKES = 117
EXPECTED_EXPOSURE_LOCATIONS = 311


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

    exposure = pd.read_csv(EXPOSURE_FILE)
    exposure = exposure[["location_id", "latitude", "longitude"]].copy()
    exposure["vs30"] = VS30

    vulnerability = pd.read_csv(VULNERABILITY_FILE)
    validate_vulnerability_curve(vulnerability)

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

    deep_events = earthquakes["depth_km"] > AKKAR_MAX_DEPTH_KM

    print(
        "Earthquakes at or below 30 km:",
        int((~deep_events).sum()),
    )
    print(
        "Earthquakes deeper than 30 km:",
        int(deep_events.sum()),
    )

    if deep_events.any():
        print(
            "WARNING: Akkar et al. (2014) states the model is intended "
            "for focal depths not greater than 30 km. Deeper events are "
            "retained for now pending guidance."
        )

    print("Earthquakes loaded:", len(earthquakes))
    print("Exposure locations loaded:", len(exposure))
    print("Damage results use the provisional vulnerability curve.")

    return earthquakes, exposure, vulnerability


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


def create_source_receiver_pairs(earthquakes, exposure):
    rows = []

    for _, earthquake in earthquakes.iterrows():
        for _, location in exposure.iterrows():
            repi_km = haversine_distance_km(
                earthquake["latitude"],
                earthquake["longitude"],
                location["latitude"],
                location["longitude"],
            )
            rhypo_km = np.hypot(repi_km, earthquake["depth_km"])

            rows.append(
                {
                    "event_id": earthquake["event_id"],
                    "origin_time": earthquake["origin_time"],
                    "magnitude": earthquake["magnitude"],
                    "magnitude_type": earthquake["magnitude_type"],
                    "rake": earthquake["rake"],
                    "source_latitude": earthquake["latitude"],
                    "source_longitude": earthquake["longitude"],
                    "source_depth_km": earthquake["depth_km"],
                    "location_id": location["location_id"],
                    "receiver_latitude": location["latitude"],
                    "receiver_longitude": location["longitude"],
                    "vs30": location["vs30"],
                    "repi_km": repi_km,
                    "rhypo_km": rhypo_km,
                    "source_within_30_km": (
                        earthquake["depth_km"] <= AKKAR_MAX_DEPTH_KM
                    ),
                    "within_200_km": rhypo_km <= 200.0,
                }
            )

    scenarios = pd.DataFrame(rows)
    print("Source-receiver pairs created:", len(scenarios))
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


def calculate_damage(results, vulnerability):
    damage = results[results["imt"] == "PGA"].copy()
    damage = damage.rename(columns={"median_value": "median_pga_g"})

    damage["damage_ratio"] = np.interp(
        damage["median_pga_g"],
        vulnerability["pga_g"],
        vulnerability["damage_ratio"],
    )

    print("Provisional damage-ratio rows calculated:", len(damage))
    return damage


def set_map_shape(ax, latitudes):
    mean_latitude = float(pd.Series(latitudes).mean())
    ax.set_aspect(1.0 / np.cos(np.radians(mean_latitude)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.25)


def plot_inputs(earthquakes, exposure):
    fig, ax = plt.subplots(figsize=(11, 6))

    ax.scatter(
        exposure["longitude"],
        exposure["latitude"],
        s=15,
        color="steelblue",
        label="Exposure locations",
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
    )

    ax.set_title("Exposure grid and selected gWFM earthquakes")
    set_map_shape(ax, exposure["latitude"])
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / "exposure_and_earthquakes.png", dpi=150)
    plt.close(fig)


def plot_pga_map(damage):
    map_results = damage[damage["event_id"] == MAP_EVENT_ID].copy()

    if map_results.empty:
        largest_event = damage.sort_values("magnitude", ascending=False).iloc[0]
        map_results = damage[
            damage["event_id"] == largest_event["event_id"]
        ].copy()

    event = map_results.iloc[0]
    event_id = event["event_id"]

    fig, ax = plt.subplots(figsize=(11, 6))
    points = ax.scatter(
        map_results["receiver_longitude"],
        map_results["receiver_latitude"],
        c=map_results["median_pga_g"],
        cmap="viridis",
        s=30,
        edgecolor="black",
        linewidth=0.2,
    )
    ax.scatter(
        event["source_longitude"],
        event["source_latitude"],
        s=180,
        marker="*",
        color="darkorange",
        edgecolor="black",
        label="Earthquake",
    )

    ax.set_title(
        f"Median PGA for gWFM event {event_id}\n"
        f"Mw {event['magnitude']:.2f}, waveform depth "
        f"{event['source_depth_km']:.1f} km"
    )
    set_map_shape(ax, map_results["receiver_latitude"])
    ax.legend()
    colorbar = fig.colorbar(points, ax=ax)
    colorbar.set_label("Median PGA (g)")
    fig.tight_layout()
    fig.savefig(OUTPUT_FOLDER / f"pga_map_{event_id}.png", dpi=150)
    plt.close(fig)


def main():
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    if RUN_BENCHMARK:
        run_benchmark()

    earthquakes, exposure, vulnerability = load_inputs()
    scenarios = create_source_receiver_pairs(earthquakes, exposure)
    results = calculate_ground_motion(scenarios)
    damage = calculate_damage(results, vulnerability)

    results.to_csv(OUTPUT_FOLDER / "ground_motion_results.csv", index=False)
    damage.to_csv(
        OUTPUT_FOLDER / "provisional_damage_ratios.csv",
        index=False,
    )

    plot_inputs(earthquakes, exposure)
    plot_pga_map(damage)

    print("Finished. Results were saved in:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
