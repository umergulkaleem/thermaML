# Heatmap Temporal Semantics

Status: repository-only investigation. No API requests were made for this note.

## Evidence Reviewed

- [fetch_and_cache.py](../../data/fetch_and_cache.py) builds the heatmap request.
- [check.py](../../check.py) contains the earlier equivalent probe payload and comments `filter_type: 3` as `Single Day`.
- [phoenix_2023-07-15_60m_tcm.json](../../data/phoenix/raw/heatmaps/phoenix_2023-07-15_60m_tcm.json) is the cached response.
- [phoenix_2023-07-15_environment_tile_7.json](../../data/phoenix/raw/environment/phoenix_2023-07-15_environment_tile_7.json) is the cached environmental response.
- [validate_data.py](../../data/validate_data.py) validates the observed environment timestamp structure.

## Heatmap Request

The existing request sends:

- `polygon_aoi`: one GeoJSON polygon
- `granularity`: `60`
- `date_time.start_date`: `2023-07-15` for the cached Phoenix request
- `date_time.filter_type`: `3`
- `analytic_type`: `tcm`

The repository does not send `end_date`, an hour, an ISO timestamp, an hourly interval, or any other time-of-day field. The only repository comment that gives `filter_type` a meaning is in `check.py`, where `3` is labeled `Single Day`.

The implementation therefore establishes a date-scoped heatmap request. It does not establish the exact temporal aggregation used inside that day.

## Cached Heatmap Response

The cached JSON has top-level keys `map_data` and `stats_data`.

Each of its 845 `map_data.features` has these property fields:

- `tile_id`
- `average_temperature`
- `min_temperature`
- `max_temperature`

All three temperature fields are scalar numbers. There are no per-feature timestamps, hourly arrays, start/end timestamps, or interval labels. `stats_data` contains spatial/distribution summaries such as minimum, maximum, mean, standard deviation, and temperature distributions; it contains no temporal metadata.

Therefore, repository evidence supports this precise statement:

> The current heatmap response is one date-scoped scalar temperature summary per returned tile, accompanied by spatial/distribution summaries. The repository does not establish whether the scalar is instantaneous, a daily aggregate, a 24-hour aggregate, or another hidden/default-time calculation.

It is not defensible to choose among those interpretations from this response alone.

## Hourly Support

The existing heatmap implementation does not expose an hourly request parameter. The repository contains no documented alternate heatmap payload with an hour, timestamp, `end_date`, or hourly filter. It also contains no cached heatmap response demonstrating multiple hourly values for the same tile.

Consequently:

- Hourly historical heatmap observations are **not established** by the current implementation.
- The repository cannot establish that the same tile can be requested at each hour from `00:00` through `23:00`.
- The interval represented by `average_temperature`, `min_temperature`, and `max_temperature` is unknown.
- A future API capability test may be necessary, but it must be separately authorized and credit-gated.

This is a limitation of the available evidence, not a claim that the external API can never support hourly heatmaps.

## Environmental Alignment

The environment response has explicit hourly metadata:

- `2023-07-15T00:00:00-07:00` through `2023-07-15T23:00:00-07:00`
- interval `1h`
- count `24`

Its environmental `temperature` equals the corresponding heatmap tile's `average_temperature` for the tested tile. The existing environmental request sends the heatmap value as the request field `temperature`, and the environment implementation preserves that payload behavior.

This equality is a direct observation. The repository does not establish whether the returned environmental temperature is:

- an echo or seed based on the supplied heatmap temperature,
- a value derived from the same underlying service,
- or an intentional documented relationship.

No causal interpretation should be made. In particular, the equality does not turn the 24 environmental values into 24 hyperlocal heatmap targets.

## Hourly Forecasting Decision

The current `average_temperature` cannot presently be used as an hourly forecasting target. Joining one date-level scalar to all 24 environmental timestamps would create repeated labels without evidence that the heatmap value applies to each hour. That would manufacture target observations and invalidate `t+1`, `t+3`, `t+6`, and `t+12` hourly evaluation.

The project must not train an hourly Linear Regression, Random Forest, or GNN model until an hourly target source or a documented temporal aggregation has been established.

## Dataset Implications

The previous 823,420-credit scenario should **not** be treated as an approved forecasting dataset plan. Its arithmetic is useful as a cost envelope, but its scientific target assumption is unresolved.

If future evidence confirms only one scalar per date, the defensible alternatives are:

1. Redesign the task as date-level or daily/spatial prediction, with one target per tile/date.
2. Use only predictors that can be aligned to that date-level target without pretending that hourly environmental values are hourly target labels.
3. Define a documented aggregation rule only if the API or an external methodological source establishes that rule.

A date-level dataset may still support spatial comparisons and a daily/spatial baseline, but it would not support the originally proposed hourly horizons.

## Model Implications

### Linear Regression

A Linear Regression baseline is appropriate only after the target resolution is fixed. With date-level targets, predictors must be aggregated or selected using information available at the date-level prediction time. Hourly environmental rows must not be repeated against one scalar target.

### Random Forest

A Random Forest can use the same date-level task and feature information as Linear Regression, but it cannot repair an unobserved target timestamp. It must not receive hourly labels created by duplication.

### GNN

A GNN can represent the cached heatmap tiles as spatial nodes for a date-level spatial task. It cannot be called a spatiotemporal forecasting model with one heatmap date. Temporal edges or temporal evaluation require multiple target dates, and hourly temporal forecasting requires hourly target observations.

## What Must Be Established Before Collection

Before spending credits on the historical plan, establish all of the following from official API documentation or an explicitly authorized, credit-gated capability test:

1. The exact meaning and interval of `average_temperature`, `min_temperature`, and `max_temperature`.
2. Whether `filter_type: 3` means a single-day aggregate and what that aggregate contains.
3. Whether the heatmap endpoint accepts an hourly timestamp, an interval, or another temporal control.
4. Whether multiple hourly heatmaps can be obtained for the same tile/date.
5. Whether historical dates beyond the cached example are supported.
6. A defensible Tucson AOI/polygon and the expected heatmap tile/cost behavior there.

Until those questions are answered, do not execute the 20-date Phoenix/Tucson collection scenario and do not train the intended hourly models.

## Current Conclusion

The current repository establishes a date-scoped scalar heatmap response and a separate 24-hour environmental context response. It does not establish an hourly hyperlocal heatmap target. The collection plan therefore needs scientific redesign or a documented heatmap temporal capability before execution. No Tucson polygon exists in the repository and none should be invented.
