# Exposure-layer input contract

No building or city-exposure dataset is included in Dashboard Version 2. The
current production result remains a 311-receiver model and must not be
presented as building-level risk.

The preferred scientifically aligned source to investigate for a future asset
extension is the GEM Global Exposure Model v2026.0.0. No GEM exposure data are
downloaded or integrated here; use would require confirmation of the available
open or licensed files and their terms.

A future exposure pilot may add a static WGS84 GeoJSON `FeatureCollection`
under this directory after its scientific use and licence have been reviewed.
Each feature should retain the original source attributes and provide:

- `feature_id`: stable source identifier;
- `source`: dataset or provider name;
- `source_url`: documented retrieval location;
- `retrieved_on`: ISO date;
- `licence`: licence or attribution identifier;
- `building`: original building tag when supplied by the source;
- `city`: source-provided or spatially validated city name, if available;
- `vulnerability_function_id`: `null` unless a documented scientific mapping
  has been approved.

Polygon or MultiPolygon building footprints are preferred. Point features may
be used only when the source itself supplies building points. A preprocessing
step must validate geometry, identifiers, attribution and feature counts, and
must produce a reasonably sized static file rather than calling a live service
from the dashboard.

At low zoom, a future implementation should show feature counts or clusters;
individual footprints should appear only at an appropriate higher zoom. Open
building tags must not be translated into GEM taxonomy codes without a
separate, evidence-backed mapping table. OpenStreetMap building footprints
would be descriptive exposure geometry only unless a defensible
building-to-GEM taxonomy mapping is developed.
