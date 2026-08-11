from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from openquake.hazardlib.gsim.akkar_2014 import AkkarEtAlRhyp2014
from openquake.hazardlib.imt import PGA, PGV, SA

from map_plotting import plot_pga_receiver_points


# Input and output files
CATALOGUE_FILE = Path("data/example_catalogue_gcmt_5.csv")
EVENT_IDS_FILE = Path("data/example_event_ids.csv")
EXPOSURE_FILE = Path("data/turkey_50km_land_grid.csv")
VULNERABILITY_FILE = Path("data/provisional_vulnerability_curve.csv")
OUTPUT_FOLDER = Path("outputs")

# Column names in the earthquake catalogue
EVENT_ID_COLUMN = "name"
LATITUDE_COLUMN = "centroid_lat"
LONGITUDE_COLUMN = "centroid_lon"
DEPTH_COLUMN = "centroid_depth_km"
MAGNITUDE_COLUMN = "Mw"
RAKE_COLUMN = "np1_rk"
ORIGIN_TIME_COLUMN = "ref_origin_time_UTC"

# Calculation settings
VS30 = 760.0
MAP_EVENT_ID = "C201003080232A"
RUN_BENCHMARK = True


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
    catalogue = pd.read_csv(CATALOGUE_FILE)
    event_ids = pd.read_csv(EVENT_IDS_FILE, dtype=str)
    exposure = pd.read_csv(EXPOSURE_FILE)
    vulnerability = pd.read_csv(VULNERABILITY_FILE)

    selected_ids = event_ids["event_id"].astype(str).str.strip()
    catalogue_ids = catalogue[EVENT_ID_COLUMN].astype(str).str.strip()
    catalogue = catalogue[catalogue_ids.isin(selected_ids)].copy()

    earthquakes = pd.DataFrame(
        {
            "event_id": catalogue[EVENT_ID_COLUMN].astype(str),
            "origin_time": catalogue[ORIGIN_TIME_COLUMN],
            "latitude": catalogue[LATITUDE_COLUMN],
            "longitude": catalogue[LONGITUDE_COLUMN],
            "depth_km": catalogue[DEPTH_COLUMN],
            "magnitude": catalogue[MAGNITUDE_COLUMN],
            "rake": catalogue[RAKE_COLUMN],
        }
    )

    exposure = exposure[["location_id", "latitude", "longitude"]].copy()
    exposure["vs30"] = VS30

    if earthquakes.empty:
        raise ValueError("No earthquake IDs matched the catalogue.")

    print("Earthquakes loaded:", len(earthquakes))
    print("Exposure locations loaded:", len(exposure))

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
                    "within_200_km": rhypo_km <= 200.0,
                }
            )

    scenarios = pd.DataFrame(rows)
    print("Source-receiver pairs created:", len(scenarios))
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

    print("Damage-ratio rows calculated:", len(damage))
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
        s=110,
        marker="*",
        color="darkorange",
        edgecolor="black",
        label="Earthquakes",
    )

    ax.set_title("Exposure grid and earthquake locations")
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
    points = plot_pga_receiver_points(ax, map_results)
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
        f"Median PGA for {event_id}\n"
        f"Mw {event['magnitude']:.2f}, depth {event['source_depth_km']:.1f} km"
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

    earthquakes, exposure, vulnerability = load_inputs()
    scenarios = create_source_receiver_pairs(earthquakes, exposure)
    results = calculate_ground_motion(scenarios)
    damage = calculate_damage(results, vulnerability)

    results.to_csv(OUTPUT_FOLDER / "ground_motion_results.csv", index=False)
    damage.to_csv(OUTPUT_FOLDER / "damage_ratios.csv", index=False)

    plot_inputs(earthquakes, exposure)
    plot_pga_map(damage)

    print("Finished. Results were saved in:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
