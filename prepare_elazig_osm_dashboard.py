"""Prepare a small, descriptive OpenStreetMap building pilot for Elazig.

The default study area is a fixed urban bounding box, not an official city or
administrative boundary.  The live dashboard never queries Overpass.
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


OSM_COPYRIGHT = "© OpenStreetMap contributors"
OSM_LICENSE = "ODbL 1.0"
OSM_SOURCE_URL = "https://www.openstreetmap.org/copyright"
DEFAULT_OVERPASS = "https://overpass-api.de/api/interpreter"
DEFAULT_BBOX = (38.66, 39.18, 38.69, 39.23)  # south, west, north, east
CLUSTER_LEVELS = {
    "overview": {"max_zoom": 9, "cell_degrees": 0.03},
    "local": {"min_zoom": 10, "max_zoom": 13, "cell_degrees": 0.008},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-input",
        type=Path,
        default=Path("data/external/osm/elazig_buildings_overpass.json"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("docs/data/exposure"),
    )
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--overpass-url", default=DEFAULT_OVERPASS)
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
        default=DEFAULT_BBOX,
    )
    parser.add_argument(
        "--retrieved-on",
        default=date.today().isoformat(),
        help="ISO retrieval date recorded in output metadata.",
    )
    return parser.parse_args()


def validate_bbox(bbox: tuple[float, float, float, float]) -> None:
    south, west, north, east = bbox
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError(f"Invalid bounding box: {bbox}")


def overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    bounds = f"{south},{west},{north},{east}"
    return (
        "[out:json][timeout:180];"
        f"way[\"building\"]({bounds});"
        "out tags geom;"
    )


def download_overpass(url: str, query: str, output: Path) -> None:
    encoded = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "TurkeyGroundMotionDashboard/1.0 research-preprocessing",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = response.read()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    area_twice = 0.0
    longitude_sum = 0.0
    latitude_sum = 0.0
    for first, second in zip(ring, ring[1:]):
        cross = first[0] * second[1] - second[0] * first[1]
        area_twice += cross
        longitude_sum += (first[0] + second[0]) * cross
        latitude_sum += (first[1] + second[1]) * cross
    if abs(area_twice) < 1e-12:
        longitudes = [point[0] for point in ring[:-1]]
        latitudes = [point[1] for point in ring[:-1]]
        return sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes)
    factor = 1.0 / (3.0 * area_twice)
    return latitude_sum * factor, longitude_sum * factor


def build_feature(
    element: dict[str, Any], retrieved_on: str
) -> tuple[dict[str, Any], tuple[float, float]] | None:
    if element.get("type") != "way" or not isinstance(element.get("id"), int):
        return None
    geometry = element.get("geometry")
    if not isinstance(geometry, list) or len(geometry) < 3:
        return None
    try:
        raw_ring = [[float(node["lon"]), float(node["lat"])] for node in geometry]
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for point in raw_ring for value in point):
        return None
    if raw_ring[0] != raw_ring[-1]:
        return None
    ring = [[round(longitude, 6), round(latitude, 6)] for longitude, latitude in raw_ring]
    if len(ring) < 4 or len({tuple(point) for point in ring[:-1]}) < 3:
        return None

    tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
    osm_id = f"way/{element['id']}"
    feature = {
        "type": "Feature",
        "id": osm_id,
        "properties": {
            "osm_id": osm_id,
            "osm_type": "way",
            "building": tags.get("building"),
            "name": tags.get("name"),
            "levels": tags.get("building:levels"),
            "source": "OpenStreetMap",
            "source_url": OSM_SOURCE_URL,
            "licence": OSM_LICENSE,
            "retrieved_on": retrieved_on,
            "vulnerability_function_id": None,
            "vulnerability_class": "Not assigned",
            "osm_tags": tags,
        },
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
    return feature, polygon_centroid(ring)


def build_geojson(
    raw: dict[str, Any],
    retrieved_on: str,
    bbox: tuple[float, float, float, float],
) -> tuple[dict[str, Any], dict[str, tuple[float, float]], int]:
    elements = raw.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Overpass response has no elements array")
    features: list[dict[str, Any]] = []
    centroids: dict[str, tuple[float, float]] = {}
    skipped = 0
    seen: set[str] = set()
    for element in elements:
        built = build_feature(element, retrieved_on)
        if built is None:
            skipped += 1
            continue
        feature, centroid = built
        osm_id = feature["properties"]["osm_id"]
        if osm_id in seen:
            raise ValueError(f"Duplicate OSM feature ID: {osm_id}")
        seen.add(osm_id)
        features.append(feature)
        centroids[osm_id] = centroid

    if not features:
        raise ValueError("No valid closed OSM building ways were found")
    features.sort(key=lambda feature: int(feature["properties"]["osm_id"].split("/")[1]))
    all_points = [
        point
        for feature in features
        for point in feature["geometry"]["coordinates"][0]
    ]
    longitudes = [point[0] for point in all_points]
    latitudes = [point[1] for point in all_points]
    geometry_bbox = [
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes),
    ]
    return (
        {
            "type": "FeatureCollection",
            "name": "Elazığ fixed urban bounding-box OSM building pilot",
            "bbox": geometry_bbox,
            "query_bbox": [bbox[1], bbox[0], bbox[3], bbox[2]],
            "features": features,
        },
        centroids,
        skipped,
    )


def build_clusters(
    features: list[dict[str, Any]],
    centroids: dict[str, tuple[float, float]],
) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    for level_name, settings in CLUSTER_LEVELS.items():
        cell_size = float(settings["cell_degrees"])
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for feature in features:
            osm_id = feature["properties"]["osm_id"]
            latitude, longitude = centroids[osm_id]
            cell = (math.floor(latitude / cell_size), math.floor(longitude / cell_size))
            grouped[cell].append(feature)

        clusters: list[dict[str, Any]] = []
        for (lat_cell, lon_cell), members in sorted(grouped.items()):
            member_centroids = [centroids[item["properties"]["osm_id"]] for item in members]
            latitudes = [item[0] for item in member_centroids]
            longitudes = [item[1] for item in member_centroids]
            tag_counts = Counter(
                (item["properties"].get("building") or "unspecified") for item in members
            )
            clusters.append(
                {
                    "cluster_id": f"{level_name}-{lat_cell}-{lon_cell}",
                    "count": len(members),
                    "latitude": round(sum(latitudes) / len(latitudes), 6),
                    "longitude": round(sum(longitudes) / len(longitudes), 6),
                    "bounds": [
                        round(min(longitudes), 6),
                        round(min(latitudes), 6),
                        round(max(longitudes), 6),
                        round(max(latitudes), 6),
                    ],
                    "top_building_tags": [
                        {"tag": tag, "count": count}
                        for tag, count in tag_counts.most_common(3)
                    ],
                }
            )
        if sum(cluster["count"] for cluster in clusters) != len(features):
            raise ValueError(f"{level_name} cluster totals do not match feature count")
        levels[level_name] = {**settings, "cluster_count": len(clusters), "clusters": clusters}

    return {
        "schema_version": 1,
        "dataset": "Elazığ OSM building pilot precomputed clusters",
        "feature_count": len(features),
        "levels": levels,
    }


def build_metadata(
    raw: dict[str, Any],
    feature_collection: dict[str, Any],
    clusters: dict[str, Any],
    retrieved_on: str,
    bbox: tuple[float, float, float, float],
    overpass_url: str,
    query: str,
    skipped: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset": "Elazığ OpenStreetMap building-footprint pilot",
        "source": "OpenStreetMap",
        "source_url": OSM_SOURCE_URL,
        "extraction_service": "Overpass API",
        "overpass_endpoint": overpass_url,
        "overpass_query": query,
        "overpass_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
        "licence": OSM_LICENSE,
        "attribution": OSM_COPYRIGHT,
        "retrieved_on": retrieved_on,
        "study_area": {
            "type": "fixed urban bounding box",
            "is_official_boundary": False,
            "description": (
                "A fixed Overpass query window around central Elazığ. It is not an "
                "official city or administrative boundary."
            ),
            "selection_semantics": (
                "Building ways intersecting the query bounding box are selected; "
                "returned polygons may extend slightly beyond the query bounds."
            ),
            "south": bbox[0],
            "west": bbox[1],
            "north": bbox[2],
            "east": bbox[3],
        },
        "feature_scope": (
            "Closed OSM ways carrying a building tag and intersecting the query "
            "bounding box"
        ),
        "feature_count": len(feature_collection["features"]),
        "skipped_non_polygon_or_invalid_elements": skipped,
        "cluster_counts": {
            name: level["cluster_count"] for name, level in clusters["levels"].items()
        },
        "limitations": [
            "OSM footprints are mapped geometry, not a complete structural inventory.",
            "OSM building tags have not been converted to GEM vulnerability taxonomy.",
            "No building-level PGA or structural-loss value is assigned.",
            "The fixed query box must not be described as Elazığ city or province extent.",
            "Returned building polygons may extend slightly beyond the Overpass query box.",
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    bbox = tuple(args.bbox)
    validate_bbox(bbox)
    query = overpass_query(bbox)
    if args.download:
        download_overpass(args.overpass_url, query, args.raw_input)
    if not args.raw_input.is_file():
        raise FileNotFoundError(
            f"{args.raw_input} does not exist; rerun with --download for a one-time extraction"
        )

    raw = json.loads(args.raw_input.read_text(encoding="utf-8-sig"))
    feature_collection, centroids, skipped = build_geojson(
        raw, args.retrieved_on, bbox
    )
    clusters = build_clusters(feature_collection["features"], centroids)
    metadata = build_metadata(
        raw,
        feature_collection,
        clusters,
        args.retrieved_on,
        bbox,
        args.overpass_url,
        query,
        skipped,
    )

    write_json(args.output_directory / "elazig_buildings.geojson", feature_collection)
    write_json(args.output_directory / "elazig_building_clusters.json", clusters)
    write_json(args.output_directory / "elazig_osm_metadata.json", metadata)
    print(f"Prepared {metadata['feature_count']} OSM building footprints")
    for level_name, count in metadata["cluster_counts"].items():
        print(f"Prepared {count} {level_name} clusters")


if __name__ == "__main__":
    main()
