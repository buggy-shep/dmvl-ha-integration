# 0006 — Options flow (minimal and full entity set)

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, second slice)

## Summary

Add an options flow that lets the user choose, per account, which entities are
created: the minimal default set (balance aggregates, unpaid documents last
payment) or the extended set (adds per-account diagnostics-style values).
Changing the options reloads the entry.

## Motivation

The phase-3 plan (D3) fixes "minimal by default, full set via options". The
first slice shipped only the minimal set and no options flow. This spec adds the
options mechanism so the entity set can grow without cluttering the registry.

## Requirements

- R1 (MUST) An options flow (`async_get_options_flow`) with boolean toggles:
  - `show_charged` — "Charged" sensor (default on);
  - `show_paid` — "Paid" sensor (default on);
  - `show_last_payment` — "Last payment" sensor (default on).
- R1b (MUST) The options flow also exposes `scan_interval_hours` (integer,
  1–24, default 6) — see spec 0007.
- R2 (MUST) `amount_due` and `unpaid_documents` are always created (the core of
  the integration) and cannot be disabled.
- R3 (MUST) Entity platforms honor the options at setup time: a disabled entity
  is not created; the enabled ones are.
- R4 (MUST) Saving options reloads the config entry (an update listener), so
  the entity set converges without a restart.
- R5 (MUST) Defaults are applied when an option is missing (backward compatible
  with entries created before this feature).
- R6 (MUST) Translations for the options form in `en.json` and `ru.json` with
  `data_description` for each toggle.

## Design

- `const.py` defines the option keys and defaults.
- A `DmvlOptionsFlow` in `config_flow.py` (registered via
  `async_get_options_flow`) shows the toggles; `__init__.py` registers an update
  listener that reloads the entry.
- `sensor.py`/`binary_sensor.py` read `entry.options` (through a small helper
  with defaults) and create only the selected entities.
- Disabled entities are not created; removing an option leaves no orphan entity
  because HA removes entities that are no longer provided on reload.

## API

- New options schema: `{show_charged: bool, show_paid: bool,
  show_last_payment: bool}` with defaults `{True, True, True}`.
- No change to the config flow data.

## Test plan

- Options flow shows the three toggles with defaults; submitting stores the
  options and reloads the entry.
- A disabled toggle results in the entity not existing; toggling back recreates
  it.
- Entries without options behave as before (all optional entities present).
- `amount_due`/`unpaid_documents` are always present regardless of options.

## Acceptance criteria

- Options tests green with full `config_flow.py` coverage; gate green; skeptic
  without `BLOCKING`.

## Out of scope

- Per-account white/black lists (only one account per entry today).
- Name-format templates and meter/receipt entities (later specs).

## Status

`implemented` (2026-10-02) — options flow with entity toggles and the polling
interval (spec 0007); an update listener reloads the entry; entities honor the
options; defaults keep entries created before the feature working.
