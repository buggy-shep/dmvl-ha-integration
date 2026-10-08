# 0020 — `unpaid_documents` reflects the current debt; add `unpaid_periods`

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (fix)
- **Supersedes:** spec 0011 R5/R6 for the `unpaid_documents` semantics

## Summary

Base the `unpaid_documents` binary sensor and the account sensor's
`unpaid_documents` attribute on the **current signed balance**
(`personal_account.has_debt`, i.e. `debt_current < 0`) instead of the library's
per-period "any charge unpaid" rule. Keep the historical, per-period view
visible through a new `unpaid_periods` attribute.

## Motivation

The expense-tracking consumer reported `binary_sensor.dmvl_<account>_unpaid_documents
= on` while the account sensor read `0` (`debt_current`) and the vendor app
showed no debt. `Session.has_unpaid_documents` (`pydmvl==0.5.0`) is
`has_debt or any(not charge.is_paid)`. The second term is unreliable: the
service allocates a payment to a different period than the one it settles, so
historical periods keep `is_paid = false` (observed with `paid = 0` and
`paid = -0.0`) even though the account is settled. The app — and the consumer's
manual reconciliation — treat the current balance as the truth.

`Charge.is_paid` (`paid >= charged_adjusted`) and the cross-period allocation
cannot be reconstructed from the snapshot, so the per-period predicate cannot
be repaired locally. The stable, app-aligned signal is `has_debt`. The raw
per-period anomaly is still reported as an attribute so it is neither hidden
nor confused with the current debt.

## Requirements

- R1 (MUST) `DmvlUnpaidDocumentsBinarySensor.is_on` is
  `coordinator.data.personal_account.has_debt` (`debt_current < 0`). At
  `debt_current >= 0` the sensor is `off`, even when historical periods have
  `is_paid = false`.
- R2 (MUST) The account sensor attribute `unpaid_documents` equals
  `personal_account.has_debt`.
- R3 (MUST) The binary sensor exposes an `unpaid_periods` attribute: a list of
  `{date, charged_adjusted, paid}` for charges with `not charge.is_paid`.
  It is an empty list when there are none (the attribute is absent when there
  are no charges at all, matching the snapshot-empty handling).
- R4 (MUST) Diagnostics report `debt_current`, `has_debt`, `has_unpaid_documents`
  (the R1 predicate) and `unpaid_periods`; the misleading raw library value is
  not presented as the account flag.
- R5 (MUST) The entity id and unique id of the binary sensor are unchanged
  (`binary_sensor.dmvl_<login>_unpaid_documents`,
  `f"{entry_id}_unpaid_documents"`) — no breaking rename (spec 0009).
- R6 (SHOULD) The binary sensor display name reflects the corrected meaning:
  EN "Debt", RU "Задолженность" (translation value only; `translation_key`
  stays `unpaid_documents`).
- R7 (MUST) This change requires no `pydmvl` release; it uses the existing
  `AccountSummary.has_debt` and `Charge` fields of `pydmvl==0.5.0`.

## Design

- `binary_sensor.py`: `is_on` → `self.coordinator.data.personal_account.has_debt`;
  add `extra_state_attributes` returning `{ATTR_UNPAID_PERIODS: [...]}` (omit
  when the snapshot has no charges).
- `sensor.py` (`DmvlAccountSensor.extra_state_attributes`): `unpaid_documents`
  → `summary.has_debt`.
- `const.py`: add `ATTR_UNPAID_PERIODS = "unpaid_periods"` and `ATTR_HAS_DEBT =
  "has_debt"`.
- `diagnostics.py`: add `has_debt` and `unpaid_periods`; set
  `has_unpaid_documents` to the integration predicate so the diagnostic matches
  the entity.
- `translations/en.json`, `translations/ru.json`: update the
  `entity.binary_sensor.unpaid_documents.name` value (R6).

## API

- State semantics of `binary_sensor.*_unpaid_documents` change to "the account
  currently owes money"; automations that relied on the historical per-period
  flag should read `unpaid_periods` instead.
- New `unpaid_periods` attribute on the binary sensor; new `has_debt` /
  `unpaid_periods` keys in diagnostics.
- No entity id, unique id, or service change.

## Test plan

- Change `test_unpaid_documents_is_on_from_unpaid_period_only` to expect `off`
  when `debt_current = 0` but a period is unsettled (red before the fix),
  renamed to `..._off_when_period_unsettled_but_no_debt`.
- Keep `..._is_on_with_debt` (debt `< 0` → `on`) and `..._off_when_settled`
  (`off`); keep `..._is_on_from_signed_balance_only` (`on` from the balance
  alone).
- New test: `unpaid_periods` lists exactly the unsettled periods with
  `date`/`charged_adjusted`/`paid`; empty when every period is settled.
- `test_sensor.py`: add a case with `debt_current = 0` and an unsettled period
  where `unpaid_documents` is `False`; keep the debt case `True`.
- `test_diagnostics.py`: assert the new keys and the aligned predicate.

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Fixing or renaming `pydmvl.Session.has_unpaid_documents` (the library
  predicate stays as-is for other consumers); tracked as a separate
  `pydmvl` spec/issue. This integration no longer uses it for its entities.
- Reconstructing true per-period settlement from payment allocation (not
  derivable from the snapshot).

## Status

`approved` (2026-10-08) — recorded user decision to ship with spec 0019 in one
branch/PR.
