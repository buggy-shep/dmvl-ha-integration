# 0008 — Payment dates on the Paid sensor

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, third slice)

## Summary

The **Paid** sensor is a period total; its `period` attribute is the charge
period, not a payment date. Expose the account payment rows on it:
`last_payment_date` (the date of the most recent payment) and `payments` (the
list of `{date, amount}` rows).

## Motivation

After the second slice a user asked where the date of the paid amount is: the
`Paid` total has no payment date, and the only payment date lives on the
separate `Last payment` sensor. The API already returns every payment row
(`personal_account.payments[]` with `fo_date`/`fo_sum`), so no new request is
needed.

## Requirements

- R1 (MUST) The **Paid** sensor carries `last_payment_date` when the latest
  payment row has a date; the value is that row's `date`. It is omitted when
  the latest row is undated (even if other rows exist).
- R2 (MUST) The **Paid** sensor carries `payments` as a list of
  `{"date": <str>, "amount": <float>}` in the API order, when non-empty.
- R3 (MUST) Both attributes are omitted when there are no payment rows; the
  sensor never raises.
- R4 (MUST) The existing `period` (charge period) and `payment_purpose`
  attributes stay unchanged, so the two dates remain distinguishable.
- R5 (MUST) `last_payment_date` is the same date the **Last payment** sensor
  reports, so the two entities agree.
- R6 (MUST) Attributes are JSON-serializable primitives.

## Design

- `sensor.py` `DmvlPaidSensor.extra_state_attributes` adds the two attributes
  from `coordinator.data.personal_account.payments`.
- `last_payment` already exposes the same row; no change there.
- No new API call; the data comes from the same snapshot.

## API

Entity attribute change only: `sensor.paid` gains `last_payment_date` and
`payments`. No config, option, or service change.

## Test plan

- With payments in the fixture: `paid` has `last_payment_date` equal to the
  latest `fo_date` and `payments` with the expected rows/amounts.
- Without payments: both attributes are absent.
- `last_payment_date` matches the `Last payment` sensor value.

## Acceptance criteria

- Tests green with full coverage of the new branches; gate green; skeptic
  without `BLOCKING`.

## Out of scope

- Full payment history as a separate sensor/event; receipt links (later specs).

## Status

`implemented` (2026-10-02) — `paid` exposes `last_payment_date` and the
`payments` list; tests cover the present/absent/undated cases.
