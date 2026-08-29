# Heatmap Temporal Capability

Status: documentation investigation plus one controlled Single Hour validation.

## Documentation Reviewed

The repository search covered:

- `/v1/heatmap`
- `filter_type`, including `filter_type: 3` and `Single Day`
- `date_time`, `start_date`, and `end_date`
- hour, timestamp, hourly, temporal, and heatmap terms
- `average_temperature`, `min_temperature`, `max_temperature`, and `tcm`
- README files, API documentation, schemas, OpenAPI/Swagger files, notebooks, examples, and sample responses

The repository contains no README, OpenAPI/Swagger specification, notebook, official API reference, schema, or sample heatmap documentation beyond the implementation and comments. `api/server.py` is empty. The available evidence is therefore:

- [fetch_and_cache.py](../../data/fetch_and_cache.py)
- [check.py](../../check.py)
- the cached [Phoenix heatmap response](../../data/phoenix/raw/heatmaps/phoenix_2023-07-15_60m_tcm.json)
- the prior [temporal semantics note](heatmap_temporal_semantics.md)

No external documentation was fetched during this no-request investigation.

## Officially Established Behavior

No official API documentation is present in the repository, so no behavior can be labeled officially established from local evidence.

The implementation sends this heatmap request shape:

- `polygon_aoi`
- `granularity: 60`
- `date_time.start_date`
- `date_time.filter_type: 3`
- `analytic_type: "tcm"`

The comment in [check.py](../../check.py) labels `filter_type: 3` as `Single Day`. This is a repository comment, not an official API definition. The code does not send `end_date`, an hour, an ISO timestamp, an interval, or an hourly flag.

The cached response has scalar per-feature fields:

- `tile_id`
- `average_temperature`
- `min_temperature`
- `max_temperature`

It has no per-feature timestamps, temporal arrays, interval metadata, or hourly observations. `stats_data` contains temperature distribution summaries and no temporal fields.

## Answers to the Capability Questions

### Meaning of `filter_type: 3`

Repository evidence labels it `Single Day`. The exact API meaning, including the timezone and aggregation interval, is unresolved.

### Meaning of `average_temperature`

Unresolved. The cached response does not say whether it is instantaneous, a daily average, a 24-hour average, or another aggregation.

### Meaning of `min_temperature` and `max_temperature`

Unresolved. The response does not identify the interval over which they are computed.

### Hourly heatmap observations

Hourly heatmap observations are not documented or demonstrated in this repository. The current request implementation exposes no hourly timestamp or time-range control. No alternate heatmap endpoint or request format is present.

### Start/end times and historical hourly requests

`start_date` is present. `end_date`, hour, timestamp, and time-range fields are absent from all local heatmap request implementations. Historical hourly support is therefore unresolved, not confirmed and not disproven.

### Other temporal heatmap endpoint

None is present in the repository. The only heatmap endpoint implemented locally is `/v1/heatmap`.

## Environmental Data Does Not Resolve This

The environment endpoint returns 24 hourly observations with explicit timestamps. Its request includes the heatmap tile's temperature as the `temperature` field, and the returned environment `temperature` matches that supplied value for the tested tile.

This is an observed request/response relationship. It does not establish that the heatmap temperature is hourly, and it does not provide 24 hyperlocal heatmap targets. Repeating one heatmap scalar across 24 environmental timestamps remains invalid.

## Is a Capability Test Necessary?

Yes, unless official FortyGuard documentation is obtained that answers the questions above.

A test is necessary because the repository cannot distinguish among:

- a date-level aggregate,
- an instantaneous value at a hidden/default time,
- a daily or 24-hour summary,
- or an undocumented temporal request mechanism.

The test must be authorized separately and must not be executed automatically.

## Minimal Proposed Capability Test

Use one existing Phoenix tile and one existing date:

- tile: `426`
- date: `2023-07-15`
- AOI: the exact cached geometry of tile `426`, if the endpoint accepts a tile-sized polygon
- analytic type: `tcm`
- granularity: `60`

The first step would be a documentation-approved request-format decision for three timestamps, for example `T0`, `T1`, and `T2`. The exact timestamp field and encoding must not be invented. If no documented timestamp field exists, the test cannot be safely formed from repository evidence.

For each successful response, preserve the complete raw JSON and compare:

- returned feature count and tile identity
- temperature fields
- response metadata
- request timestamp and requested timestamp
- credit delta

A one-tile polygon is only a proposed minimal AOI. The repository does not establish that `/v1/heatmap` accepts a tile-sized polygon or returns exactly one tile. The existing implementation accepts arbitrary polygon coordinates structurally, but that is not evidence of a server-side one-tile guarantee.

## Minimum Possible Test Cost

The only measured heatmap cost is:

- 845 returned tiles
- 4,220 credits
- approximately 4.994 credits per returned tile in that historical run

A proportional one-tile estimate would be approximately 5 credits per request, or approximately 15 credits for three timestamps. This is an engineering estimate only and is not an API guarantee.

The true minimum cost is unresolved because the repository does not establish whether billing is proportional to tile count, polygon area, request count, or another factor. If a tile-sized AOI is rejected or billing is request-based, the cost could differ substantially. Until measured, the conservative known reference is the full 4,220-credit Phoenix request, not the 5-credit estimate.

The last recorded remaining balance was 1,912,460 credits, with a snapshot preservation ceiling of 956,230 credits. It was not refreshed during this documentation-only task because the task prohibits API requests. A live credit check is required immediately before any future capability test.

## Forecasting Implications

The current intended hourly targets `t+1`, `t+3`, `t+6`, and `t+12` are not supported by the available evidence. The current collection plan must not be used to manufacture hourly labels.

Until temporal capability is resolved:

- Linear Regression can only be designed around a documented target resolution.
- Random Forest cannot recover missing target timestamps.
- A GNN can model spatial relationships for a date-level task, but it cannot be called a spatiotemporal forecasting experiment with one target date.
- No model should be trained on one scalar repeated across environmental timestamps.

If the capability test fails or documentation confirms date-level heatmaps only, redesign the project as date-level/spatial forecasting. If it succeeds, document the exact request format and rebuild the credit plan around actual temporally resolved target requests.

## Decision

**Case B is currently the correct state:** documentation does not confirm hourly heatmap observations, so a minimal capability test is needed, but it must be proposed and approved rather than executed now.

Do not start Phoenix historical collection, Tucson collection, model training, or target-label construction until:

1. the heatmap temporal request format is documented or authorized for testing;
2. the one-tile behavior and measured test cost are known; and
3. the resulting target temporal resolution is explicit.

## Controlled Single-Hour Validation

### Official Documentation

The [official FortyGuard Heatmap API documentation](https://docs-api.fortyguard.com/docs/create-heatmap) supplied for this experiment states that:

- `filter_type: 1` is `Single Hour` and requires `start_date` and `start_time`;
- `filter_type: 2` is `Range of Hours` and requires `start_date`, `start_time`, and `end_time`;
- `filter_type: 3` is `Single Day` and covers `00:00-23:59`;
- `analytic_type: "tcm"` returns temperature in degrees Celsius per tile.

### Request Used

Exactly one request was submitted with:

```json
{
  "granularity": 60,
  "analytic_type": "tcm",
  "date_time": {
    "start_date": "2023-07-15",
    "start_time": "12:00",
    "filter_type": 1
  }
}
```

The AOI was the cached geometry of Phoenix tile `426`. No `end_date`, `end_time`, or `analysis` field was added. The raw response is preserved in [phoenix_2023-07-15_12-00_tile_426_tcm.json](../../data/phoenix/raw/heatmaps/phoenix_2023-07-15_12-00_tile_426_tcm.json), and the validation record is [phoenix_2023-07-15_12-00_tile_426_validation.json](../../data/phoenix/processed/phoenix_2023-07-15_12-00_tile_426_validation.json).

### Observed API Result

The request completed and returned one feature. The response feature had `tile_id: 0`, not `tile_id: 426`. Its geometry was not identical to cached tile 426; the approximate center separation was 24.6 m. The response therefore failed the requested tile-association check. No full-polygon fallback or second heatmap request was made.

The returned feature contained:

- `average_temperature`: `41.2462 °C`
- `min_temperature`: `41.2462 °C`
- `max_temperature`: `41.2462 °C`

The response added no temporal metadata. Its `stats_data` also contained no timestamp or interval fields.

For comparison, cached Single Day tile 426 contains:

- `average_temperature`: `39.427 °C`
- `min_temperature`: `35.276 °C`
- `max_temperature`: `42.5422 °C`

The numerical differences are not a valid temporal comparison because the returned feature was not confirmed to be tile 426. They may reflect the different returned spatial cell, the different time filter, or both.

### Credit Result

The pre-request balance was 87,540 credits used and 1,912,460 remaining. The post-request balance was 91,760 used and 1,908,240 remaining. The exact request delta was **4,220 credits**, equal to the previously observed full 845-tile Phoenix heatmap charge. The activity ID was `840257c4-6189-491d-8630-c3c465970834`.

### Environment Comparison

The existing tile-426 environment response contains `2023-07-15T12:00:00-07:00`. At that timestamp, its environmental `temperature` is `39.427 °C`; the other returned values are preserved in the validation record. It is not valid to compare that value to the Single Hour response as a tile-level match because the heatmap response did not return tile 426.

### Interpretation

**Official documentation** establishes that the request format is intended to represent a Single Hour. **The observed response** establishes that the endpoint completed, returned one scalar-valued feature, and charged 4,220 credits. **The experiment does not establish temporally resolved tile-426 targets**, because the tile-sized AOI response was reindexed to tile 0 and its geometry did not match tile 426.

The result also demonstrates a critical collection constraint: a tile-sized polygon is not sufficient, from this observation, to guarantee a response feature with the requested global tile ID or exact cached geometry. The response must be spatially validated before use.

Do not collect additional hours or historical dates until the AOI-to-feature behavior is understood and a minimal request can reliably identify the intended spatial cell. Do not use the returned `41.2462 °C` as a tile-426 target.
