"""Export validated model outputs as lightweight static dashboard data.

This module does not calculate PGA or structural loss. It selects existing
receiver-level values from the complete validated output, checks them against
the tracked event-depth summary, and writes one compact JSON file per valid
event/depth-source scenario.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


DEFAULT_COMPLETE_TABLE = Path(
    "outputs_gwfm/complete_pga_structural_loss_table.csv"
)
DEFAULT_SUMMARY_TABLE = Path(
    "outputs_gwfm/complete_output/earthquake_depth_pga_loss_summary.csv"
)
DEFAULT_VULNERABILITY_MODEL = Path(
    "data/gem_vulnerability_v2026/vulnerability_structural.xml"
)
DEFAULT_OUTPUT_DIRECTORY = Path("docs/data")

EXPECTED_SCENARIO_COUNT = 321
EXPECTED_RECEIVER_COUNT = 311
EXPECTED_EVENT_COUNT = 117
VALID_DEPTH_SOURCES = ("waveform", "isc_ehb", "global_cmt")
EXPECTED_SOURCE_COUNTS = {
    "waveform": 117,
    "isc_ehb": 110,
    "global_cmt": 94,
}
CURRENT_VULNERABILITY_FUNCTION = "MUR+CLBRS/LWAL/CDN+ERN/H:1/RES"
VULNERABILITY_MODEL_VERSION = "v2026.0.0"

SCENARIO_FIELDS = (
    "location_id",
    "latitude",
    "longitude",
    "vs30_m_s",
    "median_pga_g",
    "structural_loss_ratio_mean",
    "rhypo_km",
)

DETAIL_COLUMNS = (
    "event_id",
    "depth_source",
    "location_id",
    "receiver_latitude",
    "receiver_longitude",
    "vs30_m_s",
    "median_pga_g",
    "structural_loss_ratio_mean",
    "rhypo_km",
)

SUMMARY_COLUMNS = (
    "event_id",
    "depth_source",
    "receiver_count",
    "mean_pga_g",
    "maximum_pga_g",
    "mean_structural_loss_ratio",
    "maximum_structural_loss_ratio",
)

SUMMARY_METRICS = (
    "mean_pga_g",
    "maximum_pga_g",
    "mean_structural_loss_ratio",
    "maximum_structural_loss_ratio",
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export existing receiver-level PGA and structural-loss values "
            "for the static dashboard."
        )
    )
    parser.add_argument("--complete-table", type=Path, default=DEFAULT_COMPLETE_TABLE)
    parser.add_argument("--summary-table", type=Path, default=DEFAULT_SUMMARY_TABLE)
    parser.add_argument(
        "--vulnerability-model",
        type=Path,
        default=DEFAULT_VULNERABILITY_MODEL,
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    parser.add_argument(
        "--expected-scenarios",
        type=int,
        default=EXPECTED_SCENARIO_COUNT,
    )
    parser.add_argument(
        "--expected-receivers",
        type=int,
        default=EXPECTED_RECEIVER_COUNT,
    )
    return parser


def clean_event_id(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text:
        raise ValueError("Event IDs must not be empty")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ValueError(f"Unsafe event ID for a dashboard path: {text!r}")
    return text


def event_sort_key(event_id: str) -> tuple[int, int | str]:
    return (0, int(event_id)) if event_id.isdigit() else (1, event_id)


def require_columns(
    table: pd.DataFrame,
    required: tuple[str, ...],
    table_name: str,
) -> None:
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(f"{table_name} is missing columns: {', '.join(missing)}")


def prepare_tables(
    detail: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    expected_scenarios: int = EXPECTED_SCENARIO_COUNT,
    expected_receivers: int = EXPECTED_RECEIVER_COUNT,
    expected_events: int = EXPECTED_EVENT_COUNT,
    expected_source_counts: Mapping[str, int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate source tables without recalculating scientific quantities."""

    require_columns(detail, DETAIL_COLUMNS, "Complete receiver table")
    require_columns(summary, SUMMARY_COLUMNS, "Event-depth summary")

    detail = detail.loc[:, DETAIL_COLUMNS].copy()
    summary = summary.loc[:, SUMMARY_COLUMNS].copy()
    detail["event_id"] = detail["event_id"].map(clean_event_id)
    summary["event_id"] = summary["event_id"].map(clean_event_id)
    detail["depth_source"] = detail["depth_source"].astype(str).str.strip()
    summary["depth_source"] = summary["depth_source"].astype(str).str.strip()

    invalid_sources = sorted(
        set(detail["depth_source"]).difference(VALID_DEPTH_SOURCES)
        | set(summary["depth_source"]).difference(VALID_DEPTH_SOURCES)
    )
    if invalid_sources:
        raise ValueError(f"Unexpected depth sources: {invalid_sources}")

    numeric_detail = [
        "receiver_latitude",
        "receiver_longitude",
        "vs30_m_s",
        "median_pga_g",
        "structural_loss_ratio_mean",
        "rhypo_km",
    ]
    numeric_summary = ["receiver_count", *SUMMARY_METRICS]
    for column in numeric_detail:
        detail[column] = pd.to_numeric(detail[column], errors="raise")
    for column in numeric_summary:
        summary[column] = pd.to_numeric(summary[column], errors="raise")

    if expected_source_counts is None:
        expected_source_counts = EXPECTED_SOURCE_COUNTS
    expected_source_counts = {
        source: int(expected_source_counts.get(source, 0))
        for source in VALID_DEPTH_SOURCES
    }
    if sum(expected_source_counts.values()) != expected_scenarios:
        raise ValueError(
            "Expected source counts must sum to the expected scenario count"
        )

    if len(summary) != expected_scenarios:
        raise ValueError(
            f"Expected {expected_scenarios} summary scenarios, found {len(summary)}"
        )
    summary_event_count = summary["event_id"].nunique()
    if summary_event_count != expected_events:
        raise ValueError(
            f"Expected {expected_events} unique events, found {summary_event_count}"
        )
    source_counts = {
        source: int((summary["depth_source"] == source).sum())
        for source in VALID_DEPTH_SOURCES
    }
    if source_counts != expected_source_counts:
        raise ValueError(
            f"Expected depth-source counts {expected_source_counts}, found {source_counts}"
        )
    if summary.duplicated(["event_id", "depth_source"]).any():
        raise ValueError("Event-depth summary contains duplicate scenarios")
    if detail.duplicated(["event_id", "depth_source", "location_id"]).any():
        raise ValueError("Complete receiver table contains duplicate locations")

    finite_columns = [
        "receiver_latitude",
        "receiver_longitude",
        "vs30_m_s",
        "median_pga_g",
        "structural_loss_ratio_mean",
        "rhypo_km",
    ]
    if not np.isfinite(detail[finite_columns].to_numpy(dtype=float)).all():
        raise ValueError("Complete receiver table contains non-finite values")
    if not np.isfinite(summary[numeric_summary].to_numpy(dtype=float)).all():
        raise ValueError("Event-depth summary contains non-finite numerical values")
    if not (summary["receiver_count"] == expected_receivers).all():
        raise ValueError(
            f"Every summary receiver_count must equal {expected_receivers}"
        )
    if not detail["receiver_latitude"].between(-90, 90).all():
        raise ValueError("Receiver latitude is outside -90 to 90 degrees")
    if not detail["receiver_longitude"].between(-180, 180).all():
        raise ValueError("Receiver longitude is outside -180 to 180 degrees")
    if not (detail["vs30_m_s"] > 0).all():
        raise ValueError("Vs30 values must be positive")
    if not (detail["median_pga_g"] > 0).all():
        raise ValueError("PGA values must be positive")
    if not detail["structural_loss_ratio_mean"].between(0, 1).all():
        raise ValueError("Structural loss ratios must be between zero and one")
    if not (detail["rhypo_km"] >= 0).all():
        raise ValueError("Hypocentral distances must be non-negative")

    group_columns = ["event_id", "depth_source"]
    counts = detail.groupby(group_columns, sort=False).size()
    if len(counts) != expected_scenarios:
        raise ValueError(
            f"Expected {expected_scenarios} receiver scenarios, found {len(counts)}"
        )
    detail_event_count = detail["event_id"].nunique()
    if detail_event_count != expected_events:
        raise ValueError(
            f"Expected {expected_events} unique receiver-table events, "
            f"found {detail_event_count}"
        )
    invalid_counts = counts[counts != expected_receivers]
    if not invalid_counts.empty:
        first_key = invalid_counts.index[0]
        raise ValueError(
            f"Scenario {first_key} has {int(invalid_counts.iloc[0])} receivers; "
            f"expected {expected_receivers}"
        )

    detail_keys = set(map(tuple, counts.index.tolist()))
    summary_keys = set(
        map(tuple, summary[["event_id", "depth_source"]].itertuples(index=False, name=None))
    )
    if detail_keys != summary_keys:
        missing_detail = sorted(summary_keys - detail_keys)[:5]
        missing_summary = sorted(detail_keys - summary_keys)[:5]
        raise ValueError(
            "Receiver and summary scenario sets differ: "
            f"missing receiver data={missing_detail}, missing summary rows={missing_summary}"
        )

    aggregates = (
        detail.groupby(group_columns, sort=False)
        .agg(
            mean_pga_g=("median_pga_g", "mean"),
            maximum_pga_g=("median_pga_g", "max"),
            mean_structural_loss_ratio=("structural_loss_ratio_mean", "mean"),
            maximum_structural_loss_ratio=("structural_loss_ratio_mean", "max"),
        )
        .reset_index()
    )
    comparison = summary.merge(
        aggregates,
        on=group_columns,
        suffixes=("_summary", "_receivers"),
        validate="one_to_one",
    )
    for metric in SUMMARY_METRICS:
        expected = comparison[f"{metric}_summary"].to_numpy(dtype=float)
        actual = comparison[f"{metric}_receivers"].to_numpy(dtype=float)
        if not np.allclose(expected, actual, rtol=1e-10, atol=1e-12):
            difference = np.abs(expected - actual)
            index = int(np.argmax(difference))
            row = comparison.iloc[index]
            raise ValueError(
                f"Receiver values do not reproduce {metric} for "
                f"event {row['event_id']} / {row['depth_source']}: "
                f"summary={expected[index]!r}, receivers={actual[index]!r}"
            )

    return detail, summary


def load_validated_tables(
    complete_table_path: Path,
    summary_table_path: Path,
    *,
    expected_scenarios: int = EXPECTED_SCENARIO_COUNT,
    expected_receivers: int = EXPECTED_RECEIVER_COUNT,
    expected_events: int = EXPECTED_EVENT_COUNT,
    expected_source_counts: Mapping[str, int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not complete_table_path.is_file():
        raise FileNotFoundError(f"Complete receiver table not found: {complete_table_path}")
    if not summary_table_path.is_file():
        raise FileNotFoundError(f"Event-depth summary not found: {summary_table_path}")

    detail = pd.read_csv(complete_table_path, dtype={"event_id": "string"})
    summary = pd.read_csv(summary_table_path, dtype={"event_id": "string"})
    return prepare_tables(
        detail,
        summary,
        expected_scenarios=expected_scenarios,
        expected_receivers=expected_receivers,
        expected_events=expected_events,
        expected_source_counts=expected_source_counts,
    )


def python_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Dashboard JSON cannot contain non-finite numbers")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        handle.write("\n")


def export_vulnerability_metadata(
    vulnerability_model_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if not vulnerability_model_path.is_file():
        raise FileNotFoundError(
            f"Vulnerability model not found: {vulnerability_model_path}"
        )

    namespace = {"nrml": "http://openquake.org/xmlns/nrml/0.5"}
    root = ET.parse(vulnerability_model_path).getroot()
    model = root.find("nrml:vulnerabilityModel", namespace)
    if model is None:
        raise ValueError("Vulnerability XML has no vulnerabilityModel element")

    functions: list[dict[str, Any]] = []
    for function in model.findall("nrml:vulnerabilityFunction", namespace):
        function_id = function.attrib.get("id", "").strip()
        distribution = function.attrib.get("dist", "").strip()
        imls = function.find("nrml:imls", namespace)
        imt = imls.attrib.get("imt", "").strip() if imls is not None else ""
        if not function_id or not distribution or not imt:
            raise ValueError("Vulnerability function metadata is incomplete")
        functions.append(
            {
                "function_id": function_id,
                "taxonomy_code": function_id,
                "distribution": distribution,
                "imt": imt,
                "current_production_function": (
                    function_id == CURRENT_VULNERABILITY_FUNCTION
                ),
            }
        )

    if sum(item["current_production_function"] for item in functions) != 1:
        raise ValueError(
            "The current production vulnerability function must occur exactly once"
        )

    payload = {
        "schema_version": 1,
        "model": "GEM Global Seismic Vulnerability Model",
        "model_version": VULNERABILITY_MODEL_VERSION,
        "source_file": vulnerability_model_path.as_posix(),
        "licence": "CC BY-NC-SA 4.0",
        "asset_category": model.attrib.get("assetCategory"),
        "loss_category": model.attrib.get("lossCategory"),
        "description": model.findtext(
            "nrml:description", default="", namespaces=namespace
        ).strip(),
        "function_count": len(functions),
        "current_production_function": CURRENT_VULNERABILITY_FUNCTION,
        "taxonomy_descriptions_available": False,
        "functions": functions,
    }
    write_json(output_path, payload)
    return payload


def export_dashboard_data(
    detail: pd.DataFrame,
    summary: pd.DataFrame,
    output_directory: Path,
    vulnerability_model_path: Path,
    *,
    expected_receivers: int = EXPECTED_RECEIVER_COUNT,
    source_table_path: Path = DEFAULT_COMPLETE_TABLE,
    summary_table_path: Path = DEFAULT_SUMMARY_TABLE,
) -> dict[str, Any]:
    events_directory = output_directory / "events"
    scenario_entries: list[dict[str, Any]] = []
    expected_paths: set[Path] = set()

    keys = sorted(
        {
            (row.event_id, row.depth_source)
            for row in summary[["event_id", "depth_source"]].itertuples(index=False)
        },
        key=lambda item: (event_sort_key(item[0]), VALID_DEPTH_SOURCES.index(item[1])),
    )

    for event_id, depth_source in keys:
        scenario = detail[
            (detail["event_id"] == event_id)
            & (detail["depth_source"] == depth_source)
        ].sort_values("location_id", kind="stable")

        rows = [
            [
                python_scalar(row.location_id),
                python_scalar(row.receiver_latitude),
                python_scalar(row.receiver_longitude),
                python_scalar(row.vs30_m_s),
                python_scalar(row.median_pga_g),
                python_scalar(row.structural_loss_ratio_mean),
                python_scalar(row.rhypo_km),
            ]
            for row in scenario.itertuples(index=False)
        ]

        relative_path = Path("data") / "events" / event_id / f"{depth_source}.json"
        output_path = events_directory / event_id / f"{depth_source}.json"
        expected_paths.add(output_path.resolve())
        write_json(
            output_path,
            {
                "schema_version": 1,
                "event_id": event_id,
                "depth_source": depth_source,
                "receiver_count": len(rows),
                "fields": list(SCENARIO_FIELDS),
                "receivers": rows,
            },
        )
        scenario_entries.append(
            {
                "event_id": event_id,
                "depth_source": depth_source,
                "receiver_count": len(rows),
                "path": relative_path.as_posix(),
            }
        )

    if events_directory.exists():
        for path in events_directory.rglob("*.json"):
            if path.resolve() not in expected_paths:
                path.unlink()

    vulnerability_output = output_directory / "vulnerability_functions.json"
    vulnerability = export_vulnerability_metadata(
        vulnerability_model_path,
        vulnerability_output,
    )

    manifest = {
        "schema_version": 2,
        "source_table": source_table_path.as_posix(),
        "summary_table": summary_table_path.as_posix(),
        "scenario_count": len(scenario_entries),
        "receivers_per_scenario": expected_receivers,
        "receiver_fields": list(SCENARIO_FIELDS),
        "vulnerability": {
            "model": vulnerability["model"],
            "model_version": vulnerability["model_version"],
            "licence": vulnerability["licence"],
            "function_count": vulnerability["function_count"],
            "current_production_function": vulnerability[
                "current_production_function"
            ],
            "metadata_path": "data/vulnerability_functions.json",
        },
        "scenarios": scenario_entries,
    }
    write_json(output_directory / "dashboard_manifest.json", manifest)
    return manifest


def main() -> None:
    args = build_argument_parser().parse_args()
    detail, summary = load_validated_tables(
        args.complete_table,
        args.summary_table,
        expected_scenarios=args.expected_scenarios,
        expected_receivers=args.expected_receivers,
    )
    manifest = export_dashboard_data(
        detail,
        summary,
        args.output_directory,
        args.vulnerability_model,
        expected_receivers=args.expected_receivers,
        source_table_path=args.complete_table,
        summary_table_path=args.summary_table,
    )
    print(
        "Dashboard export complete: "
        f"{manifest['scenario_count']} scenarios x "
        f"{manifest['receivers_per_scenario']} receivers"
    )


if __name__ == "__main__":
    main()
