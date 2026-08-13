# Desktop continuation handoff

Prepared: 13 August 2026

This file records the verified project state after the production-only cleanup
and public release. It is intended to let work continue from a fresh desktop
clone without relying on prior chat history.

## 1. Repository snapshot

- Repository: <https://github.com/IbaadGEO/turkey-ground-motion-risk-model>
- Branch: `main`
- Production workflow release commit:
  `48d61c941fbd55e130b3bc168d1b1db990e6ebf6`
- Commit message: `Publish production risk workflow`
- This handoff was added in a later commit. Clone the latest `main` so both the
  production release and this file are present.
- The repository now contains only the 117-event production workflow,
  production inputs and outputs, documentation, and automated validation
  tests.

For safety, use a fresh clone on the desktop. Do not merge or overwrite an old
dirty checkout.

```powershell
git clone https://github.com/IbaadGEO/turkey-ground-motion-risk-model.git
cd turkey-ground-motion-risk-model
git log -1 --oneline
git status -sb
```

Expected result:

```text
<latest commit on main>
## main...origin/main
```

The history must include `48d61c9 Publish production risk workflow`.

## 2. Current repository contents

Main code:

- `akkar_turkey_portfolio_gwfm.py`: full 117-event production calculation.
- `prepare_gwfm_catalogue.py`: gWFM parsing, selection and validation helpers.
- `map_plotting.py`: Turkey boundary and PGA plotting functions.
- `vulnerability.py`: strict OpenQuake NRML structural-vulnerability loader
  and interpolation functions.

Production data:

- `data/gwfm_v1_2_clean.csv`
- `data/gwfm_117_event_selection.csv`
- `data/turkey_50km_land_grid.csv`
- `data/turkey_boundary.geojson`
- `data/gem_vulnerability_v2026/vulnerability_structural.xml`
- `data/gem_vulnerability_v2026/LICENSE.txt`
- `data/gem_vulnerability_v2026/README.md`

Production outputs:

- `outputs_gwfm/ground_motion_results.csv`
- `outputs_gwfm/structural_loss_ratios.csv`
- `outputs_gwfm/exposure_and_earthquakes.png`
- `outputs_gwfm/pga_map_1421.png`

Tests and guides:

- `tests/test_map_plotting.py`
- `tests/test_vulnerability.py`
- `docs/LIVE_RUN_GUIDE.docx`
- `docs/OPENQUAKE_USAGE_GUIDE.docx`
- `README.md`
- `PROJECT_WALKTHROUGH.md`

## 3. Work completed

### Production earthquake workflow

- The authoritative selection contains 117 gWFM events.
- All 117 selected IDs match exactly one row in the cleaned catalogue.
- The analysis uses 311 Turkey exposure locations.
- The nested workflow creates one scenario for every valid
  event-depth-location combination.
- The current source mapping is:

| Source property | gWFM field used |
|---|---|
| Event ID | `id` |
| Origin time | `yyyymmdd` and `hhmm` |
| Longitude | `wlon` |
| Latitude | `wlat` |
| Waveform depth | `wzc` |
| ISC-EHB depth | `izc` |
| Global CMT depth | `czc`, supplemented by the supplied comparison table |
| Magnitude | `mag` |
| Magnitude type | `mty` |
| Rake | waveform `rk` |

- Rake is normalised to the range expected by the GMPE.
- Hypocentral distance is calculated as
  `Rhyp = hypot(Repi, source_depth_km)`.
- The depth table contains 117 waveform, 110 valid ISC-EHB and 94 valid
  Global CMT scenarios. Missing and non-positive depths are not guessed.
- Pairs outside the working model limits are retained and flagged rather than
  silently deleted.

### OpenQuake calculation

- GMPE: `AkkarEtAlRhyp2014` from OpenQuake HazardLib.
- Current intensity measures:
  - PGA in g
  - PGV in cm/s
  - SA(0.2 s) in g
  - SA(1.0 s) in g
- The context fields are `mag`, `rake`, `vs30` and `rhypo`.
- The OpenQuake natural-log mean is exponentiated to obtain median ground
  motion.
- Total logarithmic sigma is retained in the detailed results.
- The fixed benchmark remains inside the production script:
  - Mw 6.0
  - rake 0 degrees
  - Vs30 760 m/s
  - Repi 10.2729 km
  - depths 8 km and 15 km
  - expected PGA approximately 0.2090 g and 0.1333 g

### Maps

- Both production maps include a black Turkey outline.
- The boundary is derived from Natural Earth
  `ne_50m_admin_0_countries`, version 5.1.2, public domain.
- `exposure_and_earthquakes.png` displays all 117 selected events, including
  authoritative selected events outside the Turkey outline.
- The production PGA map uses event `1421`.
- Exact zero PGA values are grey.
- Positive PGA values use the perceptually uniform `viridis` colour map.
- Positive values use a logarithmic colour scale when their range allows it.

### Structural vulnerability

- The temporary hand-built curve was removed.
- The repository contains an unchanged copy of the GEM Global Vulnerability
  Model structural file, release `v2026.0.0`.
- Selected exact function:
  `CR/LFINF/CDL+ERL/H:2/RES`.
- Selected IMT: PGA in g.
- Distribution: beta (`BT`).
- Model SHA-256:
  `ABAAD2CBD313780E370DC1DD97DB01061FB03E58D5FA5C7590B2A879019F6116`.
- The loader checks the file hash, exact function ID, asset category, loss
  category, curve lengths, ordering, bounds and distribution parameters.
- Contents, nonstructural and fatalities/occupants models are explicitly
  rejected.
- Interpolation was compared directly with OpenQuake RiskLib and matched.
- Output terminology was changed from generic/provisional damage ratio to
  mean structural loss ratio.

Important interpretation:

- `structural_loss_ratio_mean` is conditional on the calculated median PGA.
- It is for one representative residential taxonomy at every location.
- It is not a contents loss, insured loss or complete portfolio loss.
- It does not currently integrate ground-motion uncertainty, building counts,
  replacement values or a location-specific building-taxonomy mixture.
- The GEM vulnerability data are CC BY-NC-SA 4.0 and restricted to
  non-commercial use under that licence.

### Production-only cleanup

The following demonstration or temporary material was removed:

- the five-event gCMT Python workflow;
- its example catalogue and selected-ID file;
- its CSV and map outputs;
- its Word walkthrough;
- the temporary vulnerability CSV; and
- the old provisional structural-loss output name.

Do not restore these files unless a separate demonstration workflow is
explicitly requested. Automated tests remain because they validate production
code and are not input data.

## 4. Last verified results

Tested environment:

- Python 3.12
- OpenQuake Engine 3.26.2

Verified production run:

| Check | Result |
|---|---:|
| Selected earthquakes | 117 |
| Valid event-depth scenarios | 321 |
| Exposure locations | 311 |
| Source-receiver pairs | 99,831 |
| Ground-motion result rows | 399,324 |
| Structural-loss rows | 99,831 |
| Selected IDs missing | 0 |
| Selected IDs duplicated | 0 |
| Valid depths at or below 30 km | 244 |
| Valid depths deeper than 30 km | 77 |
| Pairs within 200 km | 5,656 |
| Pairs beyond 200 km | 94,175 |
| Positive structural-loss rows | 222 |
| Maximum mean structural-loss ratio | 0.3466207197 |

Validation completed before the public push:

- Python compilation passed.
- Focused lint passed with the established E402, E501 and W503 style
  exceptions ignored.
- All 19 automated unit tests passed.
- The OpenQuake benchmark passed.
- The full 321-depth-scenario by 311-location workflow passed.
- The structural-vulnerability implementation matched OpenQuake interpolation.
- Both final PNG maps were visually inspected.
- Word guide content, OOXML structure and metadata checks passed.
- Full Word page-render inspection was not available because LibreOffice was
  not installed. Do not claim full visual DOCX validation.

## 5. Scientific invariants to preserve

Do not change these without explicit scientific approval:

- the selected 117 event IDs;
- the `wlon`, `wlat`, `wzc`, `izc`, `czc`, magnitude and waveform-rake
  mapping;
- the Haversine epicentral-distance calculation;
- `Rhyp = hypot(Repi, depth)`;
- the earthquake-by-depth-source-by-location nested calculation;
- retention and flagging of deep or distant scenarios;
- the separation of intensity-measure units;
- the exact vulnerability function and structural-only loss category; or
- the statement that structural-loss ratios are not complete or insured loss.

## 6. Current limitations

### Fixed Vs30

Every receiver still uses `VS30 = 760.0` m/s. This is the largest current
implementation limitation.

### GMPE scope

- Seventy-seven valid depth scenarios are deeper than the approximate 30 km
  applicability limit, including 25 waveform-depth scenarios.
- 94,175 event-depth-location pairs are beyond 200 km.
- These rows are retained and flagged. A scientific decision is still needed
  on whether to retain, exclude or treat them differently in later reporting.

### Single vulnerability taxonomy

One structural residential function is applied everywhere. A future building
inventory or taxonomy mixture is required for a true spatial portfolio model.

### Loss calculation

The current output uses median PGA only. It does not propagate GMPE uncertainty
through the vulnerability distribution and does not calculate monetary loss.

## 7. Remaining tasks in recommended order

### Priority 1: implement generic location-specific Vs30 sampling

External raster required: `TRVs30GeoM_9Arcsec.tif`.

The function must work for any input location table, including future 20 km and
10 km grids. It must not be tied to the current 311 rows.

Required interface and behaviour:

1. Accept an arbitrary table plus explicit location-ID, longitude and latitude
   column names.
2. Accept a declared input CRS; use EPSG:4326 only when explicitly selected.
3. Read the raster CRS from the TIFF.
4. Transform input coordinates into the raster CRS before sampling.
5. Preserve input row order and location IDs.
6. Reject duplicate IDs and non-finite coordinates.
7. Return at least:
   - `vs30_m_s`
   - raster row and column
   - sampling status
   - source-raster checksum or identifier
8. Use explicit statuses such as:
   - `valid`
   - `nodata`
   - `outside_raster`
   - `invalid_coordinate`
   - `outside_model_scope`
9. Never silently replace NoData or invalid pixels with 760 m/s.
10. If a nearest-valid fallback is added, require an explicit user-selected
    maximum search distance and record the fallback per row.

Known raster facts from the earlier read-only check; verify them again on the
desktop before implementation:

- one float32 band;
- approximately 7,109 by 4,839 pixels;
- approximately 255.54 m pixel spacing;
- NoData approximately `-3.4028234663852886e+38`;
- projected user-defined ED50 Europe Lambert Conformal Conic CRS, not native
  longitude/latitude.

Earlier preliminary sampling of the 311 current locations found:

- 305 valid pixels;
- 6 NoData pixels;
- no locations outside the raster bounds; and
- one sampled value near 14.792 m/s that requires scientific review.

Completion criteria:

- unit tests cover reordered inputs, arbitrary row counts, duplicates,
  invalid coordinates, out-of-bounds points, NoData and CRS transformation;
- the production workflow reads a `vs30_m_s` column instead of assigning 760;
- fallback policy is explicit and recorded; and
- the full portfolio is rerun and compared with the fixed-760 baseline.

### Priority 2: generate finer exposure grids

Only start after the generic Vs30 sampler works.

1. Generate or obtain the approved 20 km grid.
2. Sample Vs30 for every grid point.
3. Run and validate the full event-location matrix.
4. Review runtime, memory and output sizes.
5. Repeat for the 10 km grid if required.

Do not hard-code an expected location count into the generic sampling
function. The production workflow may keep an optional expected-count check
for a specific approved grid.

### Completed: add alternative earthquake depths

The cleaned catalogue now retains waveform (`wzc`), ISC-EHB (`izc`) and
embedded Global CMT (`czc`) depths. The supplied CMT comparison values match
all 88 overlaps and add six valid CMT depths. The workflow creates a long-form
depth table, records `-10`, missing and non-positive values explicitly, and
calculates every valid depth at every exposure location.

### Priority 4: compare depth bias and consequences

After alternative depths are available, calculate for each event, location and
IMT:

- change in depth;
- change in hypocentral distance;
- absolute and percentage change in PGA, PGV and SA;
- change in mean structural loss ratio; and
- summary bias statistics by depth catalogue.

Requested presentation output from the original checklist:

- for one approved earthquake, create comparison maps for two depth scenarios;
- show delta PGA and delta structural loss; and
- rank or summarise which depth catalogues show the largest systematic bias.

### Priority 5: extend vulnerability beyond the representative scenario

The correct structural curve is now integrated. Remaining vulnerability work
is optional and depends on the project objective:

- obtain a location-specific building inventory or taxonomy mixture;
- apply the correct structural functions and weights by location;
- decide whether to integrate ground-motion and vulnerability uncertainty;
- add building counts and replacement values only if monetary loss is needed;
  and
- continue excluding contents unless the scientific brief changes.

## 8. External files not stored in GitHub

Transfer these separately when needed and confirm their sharing permissions:

- `TRVs30GeoM_9Arcsec.tif`
- the original raw gWFM catalogue, if the cleaned CSV must be regenerated
- `117 EQ - depth comparison data.pdf`
- the five-selected-earthquakes workbook, if needed for later comparison work
- any additional GMC or replacement depth catalogue supplied later
- the original remaining-tasks checklist

The older supplied vulnerability XML/mapping bundle was GEM v2023, while the
exposure documentation was v2026. The repository deliberately uses the pinned
official v2026 structural model containing the exact selected taxonomy. Do not
replace it with the older bundle.

## 9. Desktop environment and validation commands

Create the tested Windows environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-windows-py312.txt
```

Compile and test:

```powershell
python -m py_compile `
  akkar_turkey_portfolio_gwfm.py `
  prepare_gwfm_catalogue.py `
  map_plotting.py `
  vulnerability.py

python -m unittest discover -s tests -v
```

Run the production analysis:

```powershell
python akkar_turkey_portfolio_gwfm.py
```

Before committing later work:

```powershell
git status -sb
git diff --check
```

Recheck the expected counts and inspect both PNG maps after every scientific
change.

## 10. Recommended next continuation request

Use this prompt after cloning the repository and copying the TIFF separately:

> Continue the Turkey ground-motion project from the latest public main. The
> production workflow was released in commit 48d61c9, and DESKTOP_HANDOFF.md
> records the authoritative continuation state.
> First inspect the existing production workflow and tests. Implement a shared,
> generic Vs30 raster sampler for arbitrary longitude/latitude location tables
> using TRVs30GeoM_9Arcsec.tif. Read and transform to the raster CRS, preserve
> location IDs and order, return explicit sampling statuses, and never silently
> replace NoData with 760 m/s. Add targeted tests before integrating sampled
> Vs30 into the 117-event workflow. Do not change the selected events, gWFM
> source mapping, GMPE equations, vulnerability taxonomy or retention policy.
> Run the benchmark, tests and a full comparison against the fixed-760 baseline
> before committing or pushing.
