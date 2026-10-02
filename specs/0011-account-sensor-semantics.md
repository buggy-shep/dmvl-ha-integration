# 0011 — Account sensor naming and balance semantics

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3)

## Summary

Rename the balance sensor from "Amount due" (`amount_due`) to "Account"
(`account`) and pin its semantics: the state is the raw account balance, where
a **negative** value is the amount to pay and a positive value is an
overpayment/credit. The device name combines the organization and the account
code.

## Motivation

Live data shows the balance sensor is really the account sensor: it carries all
account metadata (spec 0010), and its value is the whole-account balance, not a
per-period "amount due". The raw sign is meaningful (negative = you owe), so
the value is kept as-is rather than normalized. Device names derived from the
organization alone collide for two accounts of the same management company.

## Requirements

- R1 (MUST) The entity is renamed `amount_due` → `account` (translation key,
  entity id suffix `dmvl_<login>_account`, unique id `f"{entry_id}_account"`).
- R2 (MUST) The state is the raw `personal_account.debt_current` (`all_debt_c`)
  in RUB, `device_class: monetary`; negative = amount to pay, positive =
  overpayment. No sign normalization.
- R3 (MUST) All attributes from spec 0010 move with the renamed entity
  unchanged (`account_code`, organization, address, contacts, `period`,
  `payment_purpose`, amounts, counts, `unpaid_documents`).
- R4 (MUST) The device name is `"<organization> · <account code>"` when both
  are known, falling back to `organization`, then the login, then the
  constant. Two accounts of one organization therefore get distinct device
  names.
- R5 (MUST) `charged`, `paid`, `last_payment`, and the `unpaid_documents`
  binary sensor are unchanged.
- R6 (MUST) The `unpaid_documents` binary sensor behavior is unchanged by this
  spec: it keeps following `pydmvl`'s `has_unpaid_documents` (any unpaid charge
  period, plus the library's own debt predicate). The sign semantics introduced
  here are out of scope for that sensor.

## Design

- `sensor.py`: `DmvlAmountDueSensor` → `DmvlAccountSensor`, suffix `account`.
- `__init__.py`: `account_device_name` composes organization and login.
- Translations: `entity.sensor.account.name` = "Account" / "Лицевой счёт".
- The `unpaid_documents` state relies on `pydmvl`'s `has_unpaid_documents`,
  which is unchanged.

## API

Entity rename (breaking for automations referencing `sensor.*_amount_due`);
attribute set moves to the new entity. The device name format changes.

## Test plan

- Entity id is `sensor.dmvl_<login>_account`; unique id ends `_account`.
- State equals `all_debt_c` raw (negative stays negative).
- Account attributes are present on the new entity.
- Device name is `"<organization> · <login>"`; fallbacks covered.

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Normalizing the sign or adding a separate positive "amount to pay" entity.
- Reconciling the `unpaid_documents` / `pydmvl` `has_debt` predicate with this
  sign convention; the pre-existing behavior is left unchanged, as R6 states.

## Status

`implemented` (2026-10-02) — `amount_due` renamed to `account`, raw balance kept
with its sign, device name is organization · account code.
