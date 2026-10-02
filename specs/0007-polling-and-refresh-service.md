# 0007 — Polling interval and refresh service

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, second slice)

## Summary

Make the polling interval configurable (1–24 hours, default 6) and add a
`dmvl.refresh` service that triggers an immediate account refresh. Document the
refresh mechanics in the README.

## Motivation

The first slice hard-coded a 1-hour interval and offered no way to refresh on
demand. Account balance data changes slowly; a 6-hour default is friendlier to
the service, and a service lets automations pull fresh data after a payment.

## Requirements

- R1 (MUST) Default poll interval: **6 hours**.
- R2 (MUST) The options flow exposes `scan_interval_hours` as an integer
  selector bounded to **1–24**, defaulting to 6. A missing option falls back to
  6 (backward compatible).
- R3 (MUST) The coordinator uses the configured interval; changing the option
  reloads the entry and re-arms the timer.
- R4 (MUST) The integration registers a `dmvl.refresh` service. Without a
  target it refreshes every loaded `dmvl` entry; with an entity/device target
  it refreshes the entry(ies) owning that target.
- R5 (MUST) The service is registered once (in `async_setup`), stays available
  while at least one entry is loaded, and is removed in `async_unload_entry`
  when no loaded `dmvl` entry remains.
- R6 (MUST) The README documents: the first fetch at setup, the periodic poll,
  the configurable interval, and the `dmvl.refresh` service (with a YAML
  example).
- R7 (MUST) Refresh mechanics only read data; no account-changing call is
  introduced.

## Design

- `const.py`: `DEFAULT_SCAN_INTERVAL_HOURS = 6`, `MIN_SCAN_INTERVAL_HOURS = 1`,
  `MAX_SCAN_INTERVAL_HOURS = 24`, option key `scan_interval_hours`.
- `__init__.py` computes `timedelta(hours=option)` and passes it to the
  coordinator; registers the service in `async_setup` using
  `SupportsResponse.ONLY` (returns a small summary) or `NONE`.
- `services.yaml` describes the target; the service resolves config entries via
  the entity/device registry, or all loaded entries when untargeted.
- `config_flow.py`: the options schema adds the `NumberSelector` (min/max/step).
- The coordinator already exposes `async_refresh`; the service calls it.

## API

- New option: `scan_interval_hours` (int, 1–24, default 6).
- New service: `dmvl.refresh` (optional target; returns nothing).

## Test plan

- Default interval is 6 h when the option is absent; a configured value (e.g.
  12) is honored by the coordinator.
- Options form includes the bounded integer field with the current default.
- `dmvl.refresh` without a target triggers a coordinator refresh on the loaded
  entry (assert an extra request).
- `dmvl.refresh` with an entity target refreshes the owning entry.
- Service is removed when the last entry is unloaded (or documented if kept).

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Push/webhook updates, per-entity intervals, historical backfill.

## Status

`implemented` (2026-10-02) — configurable interval (1-24 h, default 6),
`dmvl.refresh` service, README refresh mechanics; the service is removed when
the last `dmvl` entry unloads.
