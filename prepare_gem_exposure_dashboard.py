"""Prepare compact GEM Turkiye exposure files for the static dashboard.

Only the open, aggregate v2026.0.0 summary tables are consumed.  This script
does not download or process GEM's restricted spatially disaggregated model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


GEM_VERSION = "v2026.0.0"
GEM_COMMIT = "c3add51f4e56f9d10477c8f6b5e24fd89fe089a1"
GEM_REPOSITORY = "https://github.com/gem/global_exposure_model"
GEM_COUNTRY_PATH = "Europe/Turkiye"
GEM_LICENSE = "CC BY-NC-SA 4.0"
EXPECTED_COUNTRY_ID = "TUR"
EXPECTED_PROVINCES = 81
EXPECTED_OCCUPANCIES = {"RES", "COM", "IND"}

SUMMARY_FILES = {
    "adm0": "Exposure_Summary_Adm0.csv",
    "adm1": "Exposure_Summary_Adm1.csv",
    "taxonomy": "Exposure_Summary_Taxonomy.csv",
}

ADM1_REQUIRED = {
    "ID_0",
    "NAME_0",
    "ID_1",
    "NAME_1",
    "OCCUPANCY",
    "BUILDINGS",
    "BLDG_REPL_COST_USD",
    "OCCUPANTS_TOTAL",
    "TOTAL_AREA_SQM",
}
TAXONOMY_REQUIRED = {
    "ID_0",
    "NAME_0",
    "OCCUPANCY",
    "MACRO_TAXONOMY",
    "TAXONOMY",
    "BUILDINGS",
}

MACRO_TAXONOMY_DESCRIPTIONS = {
    "ADO|ST|E": "Adobe, stone masonry, and earthen construction",
    "CR+": (
        "Reinforced concrete designed and constructed in accordance with "
        "building code requirements"
    ),
    "CR-": "Reinforced concrete with limited or no code compliance",
    "HYB": "Hybrid construction combining multiple material classes",
    "MR|MCF": "Reinforced or confined masonry",
    "MUR": "Unreinforced masonry",
    "S": "Steel construction",
    "W": "Wood, bamboo, wattle-and-daub construction",
    "OT": "Other building classes not included in the preceding categories",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary-directory",
        type=Path,
        default=Path(
            "data/external/gem_global_exposure_model_v2026/"
            "Europe/Turkiye/summaries"
        ),
        help="Directory containing the three open GEM summary CSV files.",
    )
    parser.add_argument(
        "--boundary-input",
        type=Path,
        default=Path(
            "data/external/geoboundaries/"
            "geoBoundaries-TUR-ADM1_simplified.geojson"
        ),
        help="Simplified WGS84 GeoBoundaries TUR Adm1 GeoJSON.",
    )
    parser.add_argument(
        "--boundary-metadata-input",
        type=Path,
        default=Path("data/external/geoboundaries/TUR_ADM1_metadata.json"),
        help="GeoBoundaries API metadata returned for TUR/ADM1.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("docs/data/exposure"),
    )
    parser.add_argument(
        "--retrieved-on",
        default=date.today().isoformat(),
        help="ISO retrieval date recorded in generated metadata.",
    )
    return parser.parse_args()


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name} is empty")
    return rows


def finite_nonnegative(row: dict[str, str], column: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid {column!r} value in {row}") from error
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{column} must be finite and non-negative: {value}")
    return value


def compact_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(float(value), 6)


def validate_country(rows: Iterable[dict[str, str]], source: str) -> None:
    country_ids = {row["ID_0"] for row in rows}
    if country_ids != {EXPECTED_COUNTRY_ID}:
        raise ValueError(f"{source} country IDs are not exactly TUR: {country_ids}")


def build_adm1(rows: list[dict[str, str]]) -> dict[str, Any]:
    validate_country(rows, "Adm1 summary")
    occupancies = {row["OCCUPANCY"] for row in rows}
    if occupancies != EXPECTED_OCCUPANCIES:
        raise ValueError(f"Unexpected Adm1 occupancies: {sorted(occupancies)}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        finite_nonnegative(row, "BUILDINGS")
        finite_nonnegative(row, "BLDG_REPL_COST_USD")
        finite_nonnegative(row, "OCCUPANTS_TOTAL")
        finite_nonnegative(row, "TOTAL_AREA_SQM")
        grouped[row["ID_1"]].append(row)

    if len(grouped) != EXPECTED_PROVINCES:
        raise ValueError(
            f"Expected {EXPECTED_PROVINCES} unique Adm1 units, found {len(grouped)}"
        )

    provinces: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for province_id, province_rows in grouped.items():
        names = {row["NAME_1"] for row in province_rows}
        if len(names) != 1:
            raise ValueError(f"{province_id} has inconsistent names: {names}")
        name = next(iter(names))
        if name in seen_names:
            raise ValueError(f"Duplicate Adm1 name: {name}")
        seen_names.add(name)

        if len(province_rows) != len(EXPECTED_OCCUPANCIES):
            raise ValueError(
                f"{province_id} must contain exactly one RES, COM and IND row"
            )
        by_occupancy = {row["OCCUPANCY"]: row for row in province_rows}
        if set(by_occupancy) != EXPECTED_OCCUPANCIES:
            raise ValueError(f"{province_id} does not contain RES, COM and IND")

        buildings = {
            occupancy: compact_number(
                finite_nonnegative(by_occupancy[occupancy], "BUILDINGS")
            )
            for occupancy in ("RES", "COM", "IND")
        }
        total_buildings = sum(float(value) for value in buildings.values())
        provinces.append(
            {
                "ID_0": EXPECTED_COUNTRY_ID,
                "NAME_0": province_rows[0]["NAME_0"],
                "ID_1": province_id,
                "NAME_1": name,
                "BUILDINGS": {
                    "TOTAL": compact_number(total_buildings),
                    **buildings,
                },
                "OCCUPANTS_TOTAL_RES": compact_number(
                    finite_nonnegative(by_occupancy["RES"], "OCCUPANTS_TOTAL")
                ),
                "BLDG_REPL_COST_USD": compact_number(
                    math.fsum(
                        finite_nonnegative(row, "BLDG_REPL_COST_USD")
                        for row in province_rows
                    )
                ),
                "TOTAL_AREA_SQM": compact_number(
                    math.fsum(
                        finite_nonnegative(row, "TOTAL_AREA_SQM")
                        for row in province_rows
                    )
                ),
            }
        )

    provinces.sort(key=lambda item: item["ID_1"])
    elazig = [item for item in provinces if item["ID_1"] == "TR-23"]
    if len(elazig) != 1 or elazig[0]["NAME_1"] != "Elazığ":
        raise ValueError("Expected one Elazığ province entry with ID_1=TR-23")

    return {
        "schema_version": 1,
        "dataset": "GEM Global Exposure Model Türkiye Adm1 aggregate",
        "version": GEM_VERSION,
        "country": {"ID_0": EXPECTED_COUNTRY_ID, "NAME_0": provinces[0]["NAME_0"]},
        "province_count": len(provinces),
        "occupancies": ["RES", "COM", "IND"],
        "provinces": provinces,
    }


def build_taxonomy(rows: list[dict[str, str]]) -> dict[str, Any]:
    validate_country(rows, "Taxonomy summary")
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        occupancy = row["OCCUPANCY"]
        if occupancy not in EXPECTED_OCCUPANCIES:
            raise ValueError(f"Unexpected taxonomy occupancy: {occupancy}")
        macro = row["MACRO_TAXONOMY"].strip()
        taxonomy = row["TAXONOMY"].strip()
        if not macro or not taxonomy:
            raise ValueError("Taxonomy rows require MACRO_TAXONOMY and TAXONOMY")
        grouped[(macro, taxonomy, occupancy)].append(
            finite_nonnegative(row, "BUILDINGS")
        )

    records = [
        {
            "MACRO_TAXONOMY": macro,
            "TAXONOMY": taxonomy,
            "OCCUPANCY": occupancy,
            "BUILDINGS": compact_number(math.fsum(values)),
        }
        for (macro, taxonomy, occupancy), values in grouped.items()
    ]
    records.sort(
        key=lambda item: (
            -float(item["BUILDINGS"]),
            item["MACRO_TAXONOMY"],
            item["TAXONOMY"],
            item["OCCUPANCY"],
        )
    )

    macro_totals: dict[str, float] = defaultdict(float)
    taxonomy_totals: dict[tuple[str, str, str], float] = defaultdict(float)
    for record in records:
        value = float(record["BUILDINGS"])
        macro_totals[record["MACRO_TAXONOMY"]] += value
        taxonomy_totals[
            (
                record["MACRO_TAXONOMY"],
                record["TAXONOMY"],
                record["OCCUPANCY"],
            )
        ] += value

    macro_groups = [
        {
            "MACRO_TAXONOMY": macro,
            "BUILDINGS": compact_number(total),
            "description": MACRO_TAXONOMY_DESCRIPTIONS.get(
                macro, "Description not supplied in the Türkiye README"
            ),
        }
        for macro, total in sorted(
            macro_totals.items(), key=lambda pair: (-pair[1], pair[0])
        )
    ]
    top_taxonomies = [
        {
            "MACRO_TAXONOMY": key[0],
            "TAXONOMY": key[1],
            "OCCUPANCY": key[2],
            "BUILDINGS": compact_number(total),
        }
        for key, total in sorted(
            taxonomy_totals.items(), key=lambda pair: (-pair[1], pair[0])
        )[:5]
    ]
    return {
        "schema_version": 1,
        "dataset": "GEM Global Exposure Model Türkiye taxonomy summary",
        "version": GEM_VERSION,
        "source_row_count": len(rows),
        "taxonomy_record_count": len(records),
        "macro_group_count": len(macro_groups),
        "macro_groups": macro_groups,
        "top_taxonomies": top_taxonomies,
        "records": records,
    }


def round_coordinates(value: Any, digits: int = 5) -> Any:
    if isinstance(value, list):
        return [round_coordinates(item, digits) for item in value]
    if isinstance(value, float):
        return round(value, digits)
    return value


def build_boundary(
    boundary: dict[str, Any], adm1: dict[str, Any]
) -> dict[str, Any]:
    if boundary.get("type") != "FeatureCollection":
        raise ValueError("Boundary input must be a GeoJSON FeatureCollection")
    features = boundary.get("features")
    if not isinstance(features, list) or len(features) != EXPECTED_PROVINCES:
        raise ValueError(
            f"Expected {EXPECTED_PROVINCES} boundary features, found "
            f"{len(features) if isinstance(features, list) else 'invalid'}"
        )

    exposure_by_name = {item["NAME_1"]: item for item in adm1["provinces"]}
    output_features: list[dict[str, Any]] = []
    joined_ids: set[str] = set()
    for feature in features:
        properties = feature.get("properties") or {}
        name = properties.get("shapeName")
        if name not in exposure_by_name:
            raise ValueError(f"Boundary name does not join to GEM Adm1: {name!r}")
        province = exposure_by_name[name]
        if province["ID_1"] in joined_ids:
            raise ValueError(f"Duplicate joined boundary: {province['ID_1']}")
        joined_ids.add(province["ID_1"])
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Invalid boundary geometry for {name}")
        output_features.append(
            {
                "type": "Feature",
                "id": province["ID_1"],
                "properties": {
                    "ID_0": EXPECTED_COUNTRY_ID,
                    "ID_1": province["ID_1"],
                    "NAME_1": name,
                    "shapeID": properties.get("shapeID"),
                    "source": "geoBoundaries gbOpen",
                },
                "geometry": {
                    "type": geometry["type"],
                    "coordinates": round_coordinates(geometry["coordinates"]),
                },
            }
        )

    expected_ids = {item["ID_1"] for item in adm1["provinces"]}
    if joined_ids != expected_ids:
        raise ValueError("Not all GEM Adm1 identifiers joined to the boundary")
    output_features.sort(key=lambda feature: feature["properties"]["ID_1"])
    return {
        "type": "FeatureCollection",
        "name": "Türkiye Adm1 boundaries joined to GEM exposure",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": output_features,
    }


def source_url(filename: str) -> str:
    return (
        f"{GEM_REPOSITORY}/raw/{GEM_VERSION}/{GEM_COUNTRY_PATH}/"
        f"summaries/{filename}"
    )


def build_metadata(
    adm1: dict[str, Any],
    taxonomy: dict[str, Any],
    boundary_metadata: dict[str, Any],
    retrieved_on: str,
    source_building_totals: dict[str, int | float],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_on": retrieved_on,
        "gem": {
            "dataset": "GEM Global Exposure Model",
            "country": "Türkiye",
            "scope": "Open Adm0, Adm1 and taxonomy aggregate summaries only",
            "version": GEM_VERSION,
            "commit": GEM_COMMIT,
            "repository": GEM_REPOSITORY,
            "country_readme": (
                f"{GEM_REPOSITORY}/blob/{GEM_VERSION}/{GEM_COUNTRY_PATH}/README.md"
            ),
            "source_files": {
                key: source_url(filename) for key, filename in SUMMARY_FILES.items()
            },
            "licence": GEM_LICENSE,
            "building_taxonomy_version": "GEM Building Taxonomy v4.0",
            "province_count": adm1["province_count"],
            "taxonomy_source_rows": taxonomy["source_row_count"],
            "taxonomy_records_after_settlement_aggregation": taxonomy[
                "taxonomy_record_count"
            ],
            "source_table_building_totals": source_building_totals,
            "source_table_reconciliation": (
                "The pinned GEM Adm0, Adm1 and taxonomy summaries differ slightly "
                "in total building count. Values are preserved as published rather "
                "than altered to force agreement."
            ),
            "limitations": [
                "Adm1 values are aggregate province exposure, not building locations.",
                "The restricted/full 1 km exposure model was not used.",
                "No building-level structural-loss calculation is performed.",
            ],
        },
        "boundary": {
            "dataset": "geoBoundaries gbOpen Türkiye ADM1 simplified GeoJSON",
            "api_url": "https://www.geoboundaries.org/api/current/gbOpen/TUR/ADM1/",
            "download_url": boundary_metadata.get("simplifiedGeometryGeoJSON"),
            "pinned_source_url": (
                "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/"
                "9469f09/releaseData/gbOpen/TUR/ADM1/"
                "geoBoundaries-TUR-ADM1_simplified.geojson"
            ),
            "boundary_id": boundary_metadata.get("boundaryID"),
            "boundary_year_represented": boundary_metadata.get(
                "boundaryYearRepresented"
            ),
            "source": boundary_metadata.get("boundarySource"),
            "source_update_date": boundary_metadata.get("sourceDataUpdateDate"),
            "build_date": boundary_metadata.get("buildDate"),
            "source_record_licence": boundary_metadata.get("boundaryLicense"),
            "gem_country_readme_licence": "CC BY 4.0",
            "licence_source": boundary_metadata.get("licenseSource"),
            "province_count": adm1["province_count"],
            "join_fields": ["ID_1", "NAME_1"],
            "coordinate_reference_system": "WGS84 longitude/latitude (CRS84)",
        },
        "scientific_separation": {
            "hazard_model": "Validated 311-receiver PGA and structural-loss model",
            "gem_exposure": "Aggregate province exposure only",
            "osm_buildings": "Descriptive mapped footprints only",
            "building_vulnerability_assignment": None,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    adm0_path = args.summary_directory / SUMMARY_FILES["adm0"]
    adm1_path = args.summary_directory / SUMMARY_FILES["adm1"]
    taxonomy_path = args.summary_directory / SUMMARY_FILES["taxonomy"]

    # Adm0 is read and country-validated even though the dashboard uses Adm1.
    adm0 = read_csv(adm0_path, {"ID_0", "NAME_0", "OCCUPANCY", "BUILDINGS"})
    validate_country(adm0, "Adm0 summary")
    if len(adm0) != len(EXPECTED_OCCUPANCIES) or {
        row["OCCUPANCY"] for row in adm0
    } != EXPECTED_OCCUPANCIES:
        raise ValueError("Adm0 summary must contain exactly one RES, COM and IND row")
    adm0_building_total = compact_number(
        math.fsum(finite_nonnegative(row, "BUILDINGS") for row in adm0)
    )

    adm1_rows = read_csv(adm1_path, ADM1_REQUIRED)
    taxonomy_rows = read_csv(taxonomy_path, TAXONOMY_REQUIRED)
    adm1 = build_adm1(adm1_rows)
    taxonomy = build_taxonomy(taxonomy_rows)
    source_building_totals = {
        "adm0": adm0_building_total,
        "adm1": compact_number(
            math.fsum(
                float(province["BUILDINGS"]["TOTAL"])
                for province in adm1["provinces"]
            )
        ),
        "taxonomy": compact_number(
            math.fsum(float(record["BUILDINGS"]) for record in taxonomy["records"])
        ),
    }

    boundary = json.loads(args.boundary_input.read_text(encoding="utf-8-sig"))
    boundary_metadata = json.loads(
        args.boundary_metadata_input.read_text(encoding="utf-8-sig")
    )
    joined_boundary = build_boundary(boundary, adm1)
    metadata = build_metadata(
        adm1,
        taxonomy,
        boundary_metadata,
        args.retrieved_on,
        source_building_totals,
    )

    write_json(args.output_directory / "gem_turkiye_adm1.json", adm1)
    write_json(args.output_directory / "gem_turkiye_taxonomy.json", taxonomy)
    write_json(args.output_directory / "gem_exposure_metadata.json", metadata)
    write_json(args.output_directory / "turkiye_adm1.geojson", joined_boundary)

    print(f"Prepared {adm1['province_count']} GEM Adm1 provinces")
    print(
        "Prepared "
        f"{taxonomy['taxonomy_record_count']} taxonomy records from "
        f"{taxonomy['source_row_count']} source rows"
    )


if __name__ == "__main__":
    main()
