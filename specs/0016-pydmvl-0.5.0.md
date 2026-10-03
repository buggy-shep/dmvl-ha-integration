# 0016 — pydmvl 0.5.0 pin and signed-balance fixture

- **Status:** approved
- **Scope:** `dmvl-ha-integration` dependency pin, synthetic fixture, tests

## Summary

Bump the exact `pydmvl` pin to `0.5.0` (spec 0010 there corrects the unpaid
rule) and align the synthetic fixture and tests with the corrected semantics:
the account balance is signed (a negative value means money is owed) and a
period is settled against the adjusted charge (`ist_nach100`).

## Motivation

`pydmvl` 0.4.1 derived `has_debt` from `debt_current > 0` and `is_paid` from
`paid >= charged`. The integration's fixture encoded that hypothesis (a
positive `all_debt_c` with no `ist_nach100`), so after the correction the same
fixture would read as a credit and as fully paid, flipping the primary
"unpaid documents" signal. The fixture must represent the real wire shape.

## Requirements

- R1 (MUST) `custom_components/dmvl/manifest.json` `requirements` pins
  `pydmvl==0.5.0`.
- R2 (MUST) `requirements_dev.txt` pins `pydmvl==0.5.0`.
- R3 (MUST) `manifest.json` `version` is `0.5.0` (the release tag that ships
  this change).
- R4 (MUST) The synthetic authentication fixture uses a signed balance
  (`all_debt_c < 0` when money is owed) and carries explicit `ist_nach100` in
  every `history_charges[]` entry; tests asserting the account balance or the
  paid flag are updated to match.
- R5 (MUST) No runtime code change: entities keep delegating to `pydmvl`
  (`Session.has_unpaid_documents`, `Charge.is_paid`) and to the raw
  `debt_current` for the account state (spec 0011 R2).
- R6 (MUST) The existing pin guard (spec 0015 R4) keeps asserting that the
  manifest pin equals the dev pin and the installed `pydmvl.__version__`.

## Design

- Fixture: `all_debt_b/c/e` negative (owed), `history_charges[]` entries gain
  `ist_nach100` and `ist_raz`, with one period partially paid so
  `has_unpaid_documents` is true through both terms.
- Tests: account-state expectations become negative; the "settled" cases set
  `all_debt_c` to zero and settle every charge against `ist_nach100`.

## API

No entity, service, or config-flow change; the "unpaid documents" binary
sensor and the account attributes keep their identities.

## Test plan

- Account sensor state equals the raw signed `all_debt_c` (negative stays
  negative).
- `binary_sensor.unpaid_documents` is on for a signed-debt snapshot and off
  for a settled one.
- Diagnostics report the signed debt and `has_unpaid_documents`.
- Manifest/dev pins and installed version agree.

## Acceptance criteria

- Gate green (`pytest -m "not live"`, per-module coverage threshold);
  `make ci-ha` green (hassfest + hacs/action + tests).

## Out of scope

- New entities or entity semantics changes beyond the corrected upstream
  predicates.

## Status

`approved` (2026-10-03) — supersedes the `pydmvl` pin of spec 0015.
