# Dashboard exposure datasets

This directory contains static, browser-ready exposure context. It does not
replace or alter the validated 311-receiver PGA/structural-loss model.

## GEM Global Exposure Model v2026.0.0

Official repository:
<https://github.com/gem/global_exposure_model>

Pinned country release:
<https://github.com/gem/global_exposure_model/tree/v2026.0.0/Europe/Turkiye>

Pinned release commit: `c3add51f4e56f9d10477c8f6b5e24fd89fe089a1`

Open source files used:

- <https://github.com/gem/global_exposure_model/raw/v2026.0.0/Europe/Turkiye/summaries/Exposure_Summary_Adm0.csv>
- <https://github.com/gem/global_exposure_model/raw/v2026.0.0/Europe/Turkiye/summaries/Exposure_Summary_Adm1.csv>
- <https://github.com/gem/global_exposure_model/raw/v2026.0.0/Europe/Turkiye/summaries/Exposure_Summary_Taxonomy.csv>

Licence: Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0).

Building classification: GEM Building Taxonomy v4.0.

Only open Adm0, Adm1 and taxonomy summary files are used. The restricted/full
1 km exposure model was not requested, downloaded or processed.

### Preparation and validation

Place the source CSVs under:

```text
data/external/gem_global_exposure_model_v2026/Europe/Turkiye/summaries/
```

That external-data directory is ignored by Git. Run:

```powershell
python prepare_gem_exposure_dashboard.py --retrieved-on 2026-09-03
```

The script validates required columns, country `TUR`, 81 unique Adm1 IDs and
names, exactly RES/COM/IND per province, finite non-negative values, the exact
`ID_1=TR-23` Elazığ record, taxonomy fields and the one-to-one province join.

The pinned GEM release contains a very small source-table reconciliation
difference: Adm0 totals 10,103,556 buildings, Adm1 totals 10,103,560 and the
taxonomy summary totals 10,103,501. The exporter records these published
totals and does not modify any source value to force agreement.

Outputs:

- `gem_turkiye_adm1.json`: 81 province aggregates;
- `gem_turkiye_taxonomy.json`: 1,095 exact
  `MACRO_TAXONOMY`/`TAXONOMY`/`OCCUPANCY` records after summing the source
  settlement rows; source row count is retained as 1,727;
- `gem_exposure_metadata.json`: pinned sources, licences and limitations; and
- `turkiye_adm1.geojson`: simplified WGS84 province geometry enriched with
  `ID_1` and `NAME_1` for a validated join.

The dashboard does not fetch GEM GitHub at runtime.

### Per-file licensing

The exposure directory contains material derived from multiple open datasets:

- `gem_turkiye_adm1.json` and `gem_turkiye_taxonomy.json` are derived from
  GEM Global Exposure Model v2026.0.0 and retain its CC BY-NC-SA 4.0 terms.
- `turkiye_adm1.geojson` retains the GeoBoundaries/source-record provenance
  and licence metadata documented below.
- `elazig_buildings.geojson` and `elazig_building_clusters.json` are derived
  from OpenStreetMap data under ODbL 1.0 and require
  `© OpenStreetMap contributors` attribution.

These dataset-specific terms are not replaced by any repository-level licence.

## Türkiye Adm1 boundary

GEM's v2026.0.0 Türkiye README documents its Adm1 source as GeoBoundaries,
data year 2025, under CC BY 4.0. This project therefore uses the simplified
GeoBoundaries gbOpen Türkiye Adm1 product and stores it statically.

GeoBoundaries API metadata:
<https://www.geoboundaries.org/api/current/gbOpen/TUR/ADM1/>

Pinned simplified source file:
<https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/TUR/ADM1/geoBoundaries-TUR-ADM1_simplified.geojson>

The exact API record is boundary `TUR-ADM1-25984515`, represents 2021
boundaries, was built on 2023-12-12 and contains 81 units. It identifies the
underlying source as OpenStreetMap and reports Creative Commons
Attribution-ShareAlike 2.0. GEM's README and the exact source record therefore
do not state the same licence/version metadata; both are preserved in
`gem_exposure_metadata.json` for conservative attribution.

The preprocessing script retains the source `shapeID`, joins names exactly to
GEM, assigns the GEM `ID_1`, rounds coordinates to five decimal places and
writes CRS84 longitude/latitude GeoJSON. No live boundary service is used.

## Elazığ OpenStreetMap building pilot

Source: OpenStreetMap.

Licence: Open Data Commons Open Database License 1.0 (ODbL 1.0).

Required attribution: `© OpenStreetMap contributors`.

Terms and attribution: <https://www.openstreetmap.org/copyright>

Extraction service: Overpass API,
<https://overpass-api.de/api/interpreter>.

Retrieval date: 2026-09-03.

Study area: fixed central-Elazığ urban bounding box:

```text
south=38.66, west=39.18, north=38.69, east=39.23
```

This is deliberately described as a fixed pilot bounding box. It is not an
official Elazığ city or administrative boundary and it does not cover Elazığ
province.

The one-time preprocessing query selects closed OSM ways carrying a
`building` tag that intersect the fixed query box and requests original tags
and geometry. A returned building way may extend slightly outside the query
box; the generated GeoJSON therefore stores both the query box and a separate
bounding box covering the returned geometry. Run:

```powershell
python prepare_elazig_osm_dashboard.py --download --retrieved-on 2026-09-03
```

The raw Overpass response is saved to ignored
`data/external/osm/elazig_buildings_overpass.json`. Later regeneration can be
performed without a network request:

```powershell
python prepare_elazig_osm_dashboard.py --retrieved-on 2026-09-03
```

Outputs:

- `elazig_buildings.geojson`: 1,583 building footprints;
- `elazig_building_clusters.json`: 5 overview and 30 local clusters,
  each level summing to all 1,583 footprints; and
- `elazig_osm_metadata.json`: source, licence, attribution, query, timestamp,
  study-area definition, count and limitations.

Every feature retains its OSM way ID, full original OSM tags, the original
building tag, name and levels when supplied, plus source, licence and retrieval
metadata. Missing fields remain null. Polygon coordinates are taken from the
Overpass response; invalid or genuinely non-closed ways are rejected rather
than being closed artificially.

## Scientific limitations

- GEM Adm1 values are aggregate province exposure, not building locations.
- OSM footprints are mapped geometry, not a complete structural inventory.
- OSM building tags have not been converted to GEM vulnerability taxonomy.
- `building=apartments` or `building=residential` is not treated as evidence
  for a GEM material or structural class.
- Every OSM feature has `vulnerability_function_id: null` and displays
  `Vulnerability class: Not assigned`.
- Receiver PGA and structural loss are not copied onto OSM footprints.
- No building-level structural-loss calculation has been validated.

The three concepts must remain separate: receiver model output, aggregate GEM
province exposure and descriptive OSM geometry.
