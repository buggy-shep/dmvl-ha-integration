# 0003 — Diagnostics

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3)

## Summary

A `diagnostics.py` module returns a redacted, JSON-serializable snapshot of the
config entry, its options, the integration version, and the current account
aggregates, so users can attach useful context to a bug report.

## Motivation

HA's diagnostics platform is the standard support tool and part of the quality
scale. The account snapshot contains a login (and potentially a password hash)
that must never appear in the output.

## Requirements

- R1 (MUST) `custom_components/dmvl/diagnostics.py` implements
  `async_get_config_entry_diagnostics(hass, entry)`.
- R2 (MUST) No I/O, no blocking calls, no mutation of runtime state; returns a
  plain JSON-serializable `dict`.
- R3 (MUST) The snapshot never includes the login, the password, or the
  password hash. `entry.title` and `entry.unique_id` are excluded; `entry.data`
  is passed through `async_redact_data` with both `login` and `password`. The
  output is redacted by construction from a whitelist.
- R4 (MUST) The snapshot includes: the effective config data (redacted), the
  integration version (read through `async_get_integration`), and, when the
  entry is loaded, the account aggregates (`debt_current`, `charged`, `paid`),
  `has_unpaid_documents`, and the last-payment date/amount.
- R5 (MUST) The handler tolerates a missing/`None` `entry.runtime_data` and
  still returns the entry-level snapshot.
- R6 (MUST) Tests assert, over `json.dumps(result)`, that the login and the
  password do not occur anywhere.

## Design

- A whitelist builder mirrors the entity values; dataclasses are reduced to
  scalar fields. `entry.data` is included through `async_redact_data` with the
  login as the redaction key.
- No manifest key is required: HA discovers `diagnostics.py` automatically.

## API

- New HA-standard diagnostics endpoint for the config entry; no entity, option,
  or service change.

## Test plan

- Load an entry with the mocked transport, download diagnostics, assert the
  aggregate keys and that the login/password are absent from
  `json.dumps(result)`.
- Call the handler for an entry without `runtime_data`; assert it does not
  raise.

## Acceptance criteria

- Diagnostics tests green; R1–R6 hold; gate green; skeptic without `BLOCKING`.

## Out of scope

- Device-level diagnostics, config-flow diagnostics, redacting entity ids.

## Status

`implemented` (phase-3 entry decisions recorded in the group plan, 2026-10-01:
diagnostics is part of the minimal set; implemented 2026-10-02).
