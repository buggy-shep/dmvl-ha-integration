# 0013 — Read-only entity expansion (meters, receipts, history, due segments)

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, extension slice)

## Summary

Publish the remaining read-only parts of the account snapshot as **opt-in**
entities: one sensor per meter (`Session.counters`), a receipts sensor
(`Session.receipts`), a charge-history sensor (`Session.charges`), and an
amount-due-by-channel sensor built from the `getpayments` action
(`pydmvl.PaymentOptions`). Every new entity is read-only and disabled by
default, so the minimal default set of spec 0002 is preserved (plan D3).

## Motivation

Specs 0002/0006 deliberately deferred meter readings, receipt links,
historical periods and per-channel amounts. The data is already parsed by
`pydmvl` (counters/receipts/charges since 0.3.0; payment segments since 0.4.0),
so the integration can expose it without new API probing. Keeping them behind
options avoids flooding the entity registry for users who only want the
balance aggregates.

## Requirements

- R1 (MUST) Four new boolean options, all defaulting to **off**, exposed in the
  options flow with `en.json`/`ru.json` labels and descriptions:
  `show_counters`, `show_receipts`, `show_charge_history`,
  `show_due_segments`. Entries created before this feature keep working
  (missing options fall back to the defaults).
- R2 (MUST) When `show_counters` is on, create one `sensor` per entry of
  `Session.counters`:
  - unique id `f"{entry.entry_id}_counter_{serial}"` (falling back to the
    slugified serial when the serial is empty) and stable entity id suffix
    `counter_<slug(serial)>` (`serial` is `Counter.serial`, i.e. `sch_id`);
  - name: `Counter.name` when set, else `Counter.service`, else the serial;
  - state: `Counter.current_reading.reading` when an actual reading exists,
    otherwise the latest reading by period (spec 0014 R2), else `unknown`;
  - attributes: `serial` (`sch_id`), `service` (`st_name`), `checked`
    (`sch_date_c`), a `readings` list (each
    `{period_start, period_end, reading, volume, kind, is_actual}`), and the
    submission window `submit_period_start`/`submit_period_end`/
    `submit_period_active` derived from
    `AccountInfo.settings.first_day_counters_values` /
    `last_day_counters_values`; the selected reading's `volume` (`sp_val`),
    `kind` (`sp_type`) and `period_start`/`period_end`
    (`sp_date_b`/`sp_date_e`) are also exposed, plus a top-level `is_actual`
    for the selected reading (spec 0014 R3).
- R3 (MUST) When `show_receipts` is on, create a `sensor` with suffix
  `receipts`: state is the number of `Session.receipts`; attributes expose the
  `receipts` list with `{kind, name, link}` for each
  (`kind` is `utilities` for `bills[]`, `capital_repair` for `cap_bills[]`).
  The link is short-lived; the integration does not cache or persist it beyond
  Home Assistant's normal state handling.
- R4 (MUST) When `show_charge_history` is on, create a `sensor` with suffix
  `charge_history`: state is the number of `Session.charges`; attributes expose
  the `periods` list with
  `{date, charged, charged_adjusted, benefit, difference, paid, debt_opening,
  debt_closing, is_paid}`.
- R5 (MUST) When `show_due_segments` is on, create a `sensor` with suffix
  `due_segments`: state is `PaymentOptions.count` from
  `AsyncDmvlClient.payment_segments()`; attributes expose `segments` (each
  `{payment_id, provider, button, amount, tax, tax_amount, input}`), `text`,
  and `hide_sum_with_tax`. This is the amount due *by payment channel* — it is
  not payment history (spec 0003).
- R6 (MUST) The coordinator always fetches the account snapshot. It additionally
  calls `payment_segments()` on the same poll **only** when `show_due_segments`
  is enabled. A non-authentication failure of the segments call must not fail
  the snapshot: the error is logged and the due-segments entity becomes
  unavailable while the other entities stay available. An authentication
  failure of either call triggers reauth.
- R7 (MUST) All new entities are `CoordinatorEntity` subclasses, read-only
  (`PARALLEL_UPDATES = 0`), `has_entity_name`, with stable unique ids and the
  shared per-entry device (specs 0002, 0005, 0011). A disabled family creates
  no entity.
- R8 (MUST) New entities/options have `en.json` and `ru.json` translations.
- R9 (MUST) `manifest.json` `requirements` and `requirements_dev.txt` pin
  `pydmvl==0.4.0` (spec 0008 adds `payment_segments()`); changing the library
  version updates both pins and this spec.
- R10 (MUST) Privacy: never expose the raw snapshot or the password hash;
  receipt links are runtime-only and fixtures remain synthetic.

## Design

- `const.py` gains the four option keys and defaults (`False`), the new
  attribute-key constants, and a helper for the meter submission window.
- `sensor.py` gains `DmvlCounterSensor`, `DmvlReceiptsSensor`,
  `DmvlChargeHistorySensor` and `DmvlDueSegmentsSensor`.
- The counter set is read from the first snapshot at setup; a meter that
  appears later is picked up after a reload/restart (documented limitation).
- `coordinator.py` gains `payment_options: PaymentOptions | None` and an
  `include_payment_options` flag (from the entry options). `_async_update_data`
  fetches the snapshot, then optionally the segments; `AuthError` from either
  maps to `ConfigEntryAuthFailed`, other segment errors are logged and leave
  `payment_options` as `None`. The due-segments entity overrides `available`
  to require both coordinator success and non-`None` `payment_options`.
- Numeric values are exposed as `float` in attributes (HA state/attribute
  serialization), keeping the raw `Decimal` for the state where HA expects a
  number.

## API

- `DmvlRuntimeData` is unchanged; payment options live on the coordinator.
- New options schema keys: `{show_counters, show_receipts, show_charge_history,
  show_due_segments}` (bool, default `False`).
- New sensor suffixes: `counter_<serial>`, `receipts`, `charge_history`,
  `due_segments`.
- Requires `pydmvl==0.4.0`.

## Test plan

- Counter sensor: state from the actual reading; attributes and reading
  history; absent actual reading → `unknown`; submission window from settings;
  toggle off → no entity.
- Receipts sensor: count and `receipts` list split by `bills`/`cap_bills`.
- Charge-history sensor: count and per-period attributes including `is_paid`.
- Due-segments sensor: state/attributes from a synthetic `getpayments`
  fixture; a segments failure leaves the account entities available and the
  segments sensor unavailable; `getpayments` is not called when the option is
  off.
- Options flow: the four new toggles with defaults; toggling creates/removes
  the entities.
- No real account data in fixtures; `hash`/password never exposed.

## Acceptance criteria

- Gate green on Python 3.11–3.13 (pytest, per-module coverage > 95 %);
  `make ci-ha` green (hassfest + HACS); skeptic without `BLOCKING`; release
  tagged with the manifest version.

## Out of scope

- Any account-changing action (submitting/deleting readings, payments) — needs
  a separate spec with explicit user confirmation.
- Per-account white/black lists and name-format templates.
- Dynamically adding sensors for meters that appear after setup without a
  reload.

## Status

`approved` (2026-10-03, recorded decision: user instructed implementation of the
phase-3 read-only entity expansion). `pydmvl` payment segments (0.4.0) are
developed in parallel; the due-segments parts (R5/R6) land once that release is
published.
