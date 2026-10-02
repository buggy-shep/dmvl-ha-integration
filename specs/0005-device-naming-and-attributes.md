# 0005 — Device naming and entity attributes

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, second slice)

## Summary

Name the account device after the account itself (so two accounts are
distinguishable) and enrich the money sensors with meaningful attributes and
descriptions, including the dates the API provides.

## Motivation

The first slice named every device `Domovladelets`, so two accounts were
indistinguishable in the UI, and the three monetary sensors exposed only a bare
number with no explanation. The API does provide date information for the
account period and the charge/payment rows.

## Requirements

- R1 (MUST) Device name: the account name from the snapshot (`Session.name`),
  falling back to the account login when the name is absent, then to
  `Domovladelets`. Two accounts therefore get distinct default names.
- R2 (MUST) The device name must be derived from data only — no secret is
  exposed beyond what the user's own account already reveals; the device
  registry already contains the account login via the config entry title, so
  the account name is not additional exposure.
- R3 (MUST) Money sensors carry explanatory attributes:
  - `amount_due`: `period` (the account `fun_date`, the calculation date) when
    present;
  - `charged` / `paid`: `period` (the latest `history_charges[]` `ist_date`)
    when present;
  - all three: `payment_purpose` (the API `textOplUsl`) when present.
- R4 (MUST) The money sensors keep `device_class: monetary` and the RUB unit,
  but no longer declare `state_class: total` (they are per-period aggregates,
  not cumulative totals).
- R5 (MUST) `last_payment` keeps its date value and amount attribute; the
  amount attribute is complete and the sensor stays diagnostic-free.
- R6 (MUST) All attributes are JSON-serializable primitives (strings/floats);
  missing values are omitted.

## Design

- `entity.py` builds `DeviceInfo(name=...)` from the runtime data account name,
  not a constant.
- `__init__.py` resolves the device name from the first snapshot and stores it
  in `DmvlRuntimeData`; the device is registered/updated on setup.
- `sensor.py` adds `extra_state_attributes` to the money sensors from the
  coordinator snapshot.
- Attributes use the already-public account fields; no new API call is made.

## API

No integration-level API change. Device registry name changes from a constant
to the account name; entity attributes gain `period` and `payment_purpose`.

## Test plan

- Device name = snapshot `name`; fallback to login when the snapshot name is
  empty; fallback to the constant when both are absent.
- Money sensor attributes include `period`/`payment_purpose` when the fixture
  provides them and omit them when absent.
- `state_class` is absent on the money sensors.
- Two entries produce two distinct device names.

## Acceptance criteria

- Tests green with full coverage of the new branches; gate green; skeptic
  without `BLOCKING`.

## Out of scope

- Meter readings, receipts, per-segment amounts, history sensors (later specs).
- Renaming devices from the UI (HA already allows it).

## Status

`implemented` (2026-10-02) — device name from `Session.name` with login/
constant fallback; money sensors expose `period`/`payment_purpose` and drop
`state_class`; tests cover the fallbacks, attributes and two-account case.
