# 0014 — Meter sensor state falls back to the latest reading

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (fix for spec 0013 R2)

## Summary

When the service does not mark any meter reading as actual (`isActual` is
false for every period), the meter sensor state becomes
`unknown` even though readings exist. This spec changes the state to fall back
to the most recent reading by period end, and records whether the selected
reading was the actual one.

## Motivation

Spec 0013 R2 uses `Counter.current_reading` (the reading flagged actual) as the
sensor state. The service returns `isActual: false` for all readings
outside the monthly submission window (and when no current-period reading
exists yet), so the sensor shows `unknown` although the reading history is
available. Showing the latest known reading is the useful behavior.

## Requirements

- R1 (MUST) When a reading is flagged actual, the sensor keeps using it (spec
  0013 R2 unchanged).
- R2 (MUST) When no reading is flagged actual, the state is the reading with
  the greatest `period_end` (lexicographic on the ISO date; `period_start`
  breaks ties). A reading without a `period_end` is selected only when it is
  the only reading. If there are no readings at all, the state stays
  `unknown`.
- R3 (MUST) The volume/kind/period attributes follow the selected reading, and
  a top-level `is_actual` attribute reports whether the selected reading is
  the actual one (`false` when it is the fallback).
- R4 (MUST) Tests cover: actual preferred; fallback to latest by `period_end`;
  unsorted reading order; no readings → `unknown`.

## Design

- The selection lives in `sensor.DmvlCounterSensor` (the library's
  `Counter.current_reading` keeps its strict meaning). A small helper picks the
  actual reading, else the latest by `period_end`.
- No change to entity ids, options or the library dependency.

## Test plan

- Meter fixture without any actual reading → state is the newest reading,
  `is_actual` is `false`, and `volume`/`kind`/`period_*` follow that fallback
  reading.
- Fixture with an actual reading → state is that reading, `is_actual` is
  `true`, regardless of order (including an older actual reading that beats a
  newer non-actual one).
- Counter with an empty `values[]` → `unknown`.

## Acceptance criteria

- Gate green, per-module coverage > 95 %, `make ci-ha` green, skeptic without
  `BLOCKING`; released as a patch version.

## Out of scope

- Changing the library's `Counter.current_reading` semantics.
- Submitting readings (account-changing).

## Status

`approved` (2026-10-03, recorded decision: user chose "fallback to the latest
reading" for meters with no actual reading). Supersedes the "otherwise
`unknown`" clause of spec 0013 R2.
