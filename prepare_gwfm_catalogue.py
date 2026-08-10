from pathlib import Path
import sys

import numpy as np
import pandas as pd


FIELD_POSITIONS = {
    "id": 0,
    "yyyymmdd": 1,
    "hhmm": 2,
    "wlon": 3,
    "wlat": 4,
    "wzc": 5,
    "waveform_rk": 19,
    "mag": 25,
    "mty": 26,
}

MINUS_SIGNS = ["−", "‐", "‑", "‒", "–", "—", "﹣", "－"]


def normalise_minus_signs(text):
    for minus_sign in MINUS_SIGNS:
        text = text.replace(minus_sign, "-")
    return text


def normalise_rake(rake_values):
    return ((rake_values + 180.0) % 360.0) - 180.0


def load_gwfm_catalogue(file_path):
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8-sig")
    minus_sign_count = sum(text.count(sign) for sign in MINUS_SIGNS)
    lines = text.splitlines()

    if len(lines) < 3:
        raise ValueError("The gWFM file does not contain a header and data rows.")

    header = normalise_minus_signs(lines[1]).split()
    for field_name, position in FIELD_POSITIONS.items():
        expected_name = "rk" if field_name == "waveform_rk" else field_name
        if position >= len(header) or header[position] != expected_name:
            raise ValueError(
                f"The expected gWFM field '{expected_name}' was not found "
                f"at position {position}."
            )

    rows = []

    for line_number, line in enumerate(lines[2:], start=3):
        if not line.strip():
            continue

        tokens = normalise_minus_signs(line).split()

        if len(tokens) <= FIELD_POSITIONS["mty"]:
            raise ValueError(f"Could not read gWFM data on line {line_number}.")

        rows.append(
            {
                "event_id": tokens[FIELD_POSITIONS["id"]],
                "yyyymmdd": tokens[FIELD_POSITIONS["yyyymmdd"]],
                "hhmm": tokens[FIELD_POSITIONS["hhmm"]],
                "longitude": tokens[FIELD_POSITIONS["wlon"]],
                "latitude": tokens[FIELD_POSITIONS["wlat"]],
                "depth_km": tokens[FIELD_POSITIONS["wzc"]],
                "magnitude": tokens[FIELD_POSITIONS["mag"]],
                "magnitude_type": tokens[FIELD_POSITIONS["mty"]],
                "rake": tokens[FIELD_POSITIONS["waveform_rk"]],
            }
        )

    catalogue = pd.DataFrame(rows)

    if catalogue.empty:
        raise ValueError("No gWFM earthquake records were found.")

    catalogue["event_id"] = catalogue["event_id"].astype(str).str.strip()

    if catalogue["event_id"].duplicated().any():
        duplicate_ids = catalogue.loc[
            catalogue["event_id"].duplicated(keep=False), "event_id"
        ].unique()
        raise ValueError(
            "Duplicate event IDs were found in gWFM: "
            + ", ".join(sorted(duplicate_ids))
        )

    date_and_time = catalogue["yyyymmdd"] + catalogue["hhmm"]
    catalogue["origin_time"] = pd.to_datetime(
        date_and_time,
        format="%Y%m%d%H%M",
        errors="coerce",
    )

    numeric_columns = ["longitude", "latitude", "depth_km", "magnitude", "rake"]
    for column in numeric_columns:
        catalogue[column] = pd.to_numeric(catalogue[column], errors="coerce")

    invalid_times = catalogue["origin_time"].isna()
    if invalid_times.any():
        invalid_ids = catalogue.loc[invalid_times, "event_id"].tolist()
        raise ValueError("Invalid gWFM dates or times: " + ", ".join(invalid_ids))

    required_numeric = ["longitude", "latitude", "depth_km", "magnitude"]
    invalid_numeric = catalogue[required_numeric].isna().any(axis=1)
    if invalid_numeric.any():
        invalid_ids = catalogue.loc[invalid_numeric, "event_id"].tolist()
        raise ValueError("Invalid required gWFM values: " + ", ".join(invalid_ids))

    rakes_to_wrap = catalogue["rake"].notna() & (
        (catalogue["rake"] < -180.0) | (catalogue["rake"] > 180.0)
    )
    catalogue.loc[catalogue["rake"].notna(), "rake"] = normalise_rake(
        catalogue.loc[catalogue["rake"].notna(), "rake"]
    )

    cleaned = catalogue[
        [
            "event_id",
            "origin_time",
            "longitude",
            "latitude",
            "depth_km",
            "magnitude",
            "magnitude_type",
            "rake",
        ]
    ].copy()

    print("gWFM records loaded:", len(cleaned))
    print("Unusual minus signs normalised:", minus_sign_count)
    print("Missing waveform rakes:", cleaned["rake"].isna().sum())
    print("Rakes wrapped to -180 to 180 degrees:", rakes_to_wrap.sum())
    print("Magnitude types:")
    print(cleaned["magnitude_type"].value_counts().to_string())

    return cleaned


def print_id_report(label, event_ids):
    event_ids = [str(event_id) for event_id in event_ids]
    print(f"{label} ({len(event_ids)}):")
    print(", ".join(event_ids) if event_ids else "None")


def select_gwfm_events(catalogue, selection_file, selection_id_column):
    selection = pd.read_csv(selection_file, dtype=str)

    if selection_id_column not in selection.columns:
        raise ValueError(
            f"Selection column '{selection_id_column}' was not found. "
            f"Available columns: {', '.join(selection.columns)}"
        )

    requested = selection[selection_id_column].fillna("").astype(str).str.strip()
    blank_rows = requested == ""
    requested_ids = requested[~blank_rows].tolist()

    duplicate_requested = sorted(
        requested[requested.duplicated(keep=False) & ~blank_rows].unique().tolist()
    )

    catalogue_ids = catalogue["event_id"].astype(str).str.strip()
    duplicate_catalogue = sorted(
        catalogue_ids[
            catalogue_ids.duplicated(keep=False) & catalogue_ids.isin(requested_ids)
        ]
        .unique()
        .tolist()
    )

    available_ids = set(catalogue_ids)
    matched_ids = [event_id for event_id in requested_ids if event_id in available_ids]
    missing_ids = sorted(set(requested_ids) - available_ids)

    print_id_report("Requested IDs", requested_ids)
    print_id_report("Matched IDs", matched_ids)
    print_id_report("Missing IDs", missing_ids)
    print_id_report(
        "Duplicate IDs",
        sorted(set(duplicate_requested + duplicate_catalogue)),
    )

    problems = []

    if blank_rows.any():
        problems.append(f"{blank_rows.sum()} blank event ID row(s)")
    if missing_ids:
        problems.append("missing event IDs")
    if duplicate_requested:
        problems.append("duplicate IDs in the selection file")
    if duplicate_catalogue:
        problems.append("duplicate selected IDs in the gWFM catalogue")

    if problems:
        raise ValueError("Event-ID validation failed: " + "; ".join(problems))

    requested_table = pd.DataFrame({"event_id": requested_ids})
    selected = requested_table.merge(
        catalogue,
        on="event_id",
        how="left",
        validate="one_to_one",
    )

    validate_selected_earthquakes(selected)
    return selected


def validate_selected_earthquakes(earthquakes):
    required_columns = [
        "event_id",
        "origin_time",
        "longitude",
        "latitude",
        "depth_km",
        "magnitude",
        "magnitude_type",
        "rake",
    ]

    missing_columns = [
        column for column in required_columns if column not in earthquakes.columns
    ]
    if missing_columns:
        raise ValueError(
            "Selected earthquake table is missing columns: "
            + ", ".join(missing_columns)
        )

    problems = []
    numeric_columns = ["longitude", "latitude", "depth_km", "magnitude", "rake"]
    numeric_values = earthquakes[numeric_columns].apply(pd.to_numeric, errors="coerce")

    for column in numeric_columns:
        invalid = ~np.isfinite(numeric_values[column])
        if invalid.any():
            event_ids = earthquakes.loc[invalid, "event_id"].astype(str).tolist()
            print_id_report(f"Events with unusable {column}", event_ids)
            problems.append(f"unusable {column}")

    checks = {
        "longitude outside -180 to 180": (
            (numeric_values["longitude"] < -180.0)
            | (numeric_values["longitude"] > 180.0)
        ),
        "latitude outside -90 to 90": (
            (numeric_values["latitude"] < -90.0)
            | (numeric_values["latitude"] > 90.0)
        ),
        "negative depth": numeric_values["depth_km"] < 0.0,
        "non-positive magnitude": numeric_values["magnitude"] <= 0.0,
        "rake outside -180 to 180": (
            (numeric_values["rake"] < -180.0) | (numeric_values["rake"] > 180.0)
        ),
    }

    for label, invalid in checks.items():
        invalid = invalid.fillna(False)
        if invalid.any():
            event_ids = earthquakes.loc[invalid, "event_id"].astype(str).tolist()
            print_id_report(f"Events with {label}", event_ids)
            problems.append(label)

    magnitude_types = earthquakes["magnitude_type"].fillna("").astype(str).str.strip()
    non_mw = magnitude_types != "Mw"
    if non_mw.any():
        event_ids = earthquakes.loc[non_mw, "event_id"].astype(str).tolist()
        print_id_report("Events with a non-Mw magnitude", event_ids)
        problems.append("non-Mw magnitudes")

    if problems:
        raise ValueError(
            "Selected earthquake validation failed: "
            + "; ".join(sorted(set(problems)))
        )

    print("Selected earthquake inputs passed validation:", len(earthquakes))


def validate_vulnerability_curve(vulnerability):
    required_columns = ["pga_g", "damage_ratio"]
    missing_columns = [
        column for column in required_columns if column not in vulnerability.columns
    ]

    if missing_columns:
        raise ValueError(
            "Vulnerability table is missing columns: " + ", ".join(missing_columns)
        )

    if vulnerability.empty:
        raise ValueError("The vulnerability table is empty.")

    pga_values = pd.to_numeric(vulnerability["pga_g"], errors="coerce")
    damage_ratios = pd.to_numeric(vulnerability["damage_ratio"], errors="coerce")

    if not np.isfinite(pga_values).all():
        raise ValueError("The vulnerability table contains an unusable PGA value.")
    if not np.isfinite(damage_ratios).all():
        raise ValueError("The vulnerability table contains an unusable damage ratio.")
    if (pga_values.diff().dropna() <= 0.0).any():
        raise ValueError("Vulnerability PGA values must increase from low to high.")
    if ((damage_ratios < 0.0) | (damage_ratios > 1.0)).any():
        raise ValueError("Vulnerability damage ratios must stay between 0 and 1.")

    print("Vulnerability curve passed validation:", len(vulnerability), "points")


def print_distance_summary(scenarios):
    if "within_200_km" not in scenarios.columns:
        raise ValueError("The scenario table does not contain 'within_200_km'.")

    within_200_km = scenarios["within_200_km"]

    if within_200_km.isna().any():
        raise ValueError("The distance summary contains missing 200 km flags.")

    within_count = int(within_200_km.astype(bool).sum())
    beyond_count = int(len(scenarios) - within_count)

    print("Pairs within 200 km:", within_count)
    print("Pairs beyond 200 km:", beyond_count)


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python prepare_gwfm_catalogue.py "
            "path/to/gWFM_v1.2.txt data/gwfm_v1_2_clean.csv"
        )
        raise SystemExit(1)

    source_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    cleaned = load_gwfm_catalogue(source_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_file, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print("Cleaned gWFM catalogue saved to:", output_file)


if __name__ == "__main__":
    main()
