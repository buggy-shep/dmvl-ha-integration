# 0010 — Account attributes on the balance sensor

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3)

## Summary

Turn the **Amount due** balance sensor into the account sensor: keep the
balance as its state and expose the account-screen metadata (account code,
address, provider, service, period, contact fields, counts) as attributes —
every scalar value from the login response that is safe to publish in Home
Assistant state.

## Motivation

The reference approach for this integration exposes one balance `sensor` per account
carrying the account metadata as attributes (`account_code`, `address`,
`provider_name`, `service_name`, `status`, …). Doing the same makes the `dmvl`
device self-describing and lets users reference account fields in automations
without extra entities.

## Requirements

- R1 (MUST) The balance sensor keeps its monetary state (`debt_current`, RUB,
  `device_class: monetary`) and gains account attributes from the snapshot.
- R2 (MUST) Attributes (whitelist, only when present):
  - identity: `account_code` (login), `database`, `organization` (`name`),
    `full_name` (`fls_fio`);
  - address: `address` (`maddr`), `flat` (`mflat`, trimmed), `management_key`
    (`mgfkey`);
  - contacts: `developer_email` (`dev_email`), `contact_email` (`memail`),
    `contact_phone` (`usersInfo.phone`);
  - service: `period` (`fun_date`), `payment_purpose` (`textOplUsl`),
    `opening_balance` (`all_debt_b`), `charged` (`all_nach`),
    `adjustment` (`all_raz`), `paid` (`all_opl`), `closing_balance`
    (`all_debt_e`);
  - flags: `unpaid_documents` (bool);
  - counts: `charge_periods`, `payment_count`, `counters`, `receipts`, `news`.

  The account-sensor payment count is named `payment_count` to avoid clashing
  with the Paid sensor's `payments` list (different type, same idea).
- R3 (MUST) No secret or credential is exposed: the `hash`, the login
  password, and the password hash never appear. `login` is exposed only as
  `account_code`.
- R4 (MUST) Every attribute is a JSON-serializable primitive (str/int/float/
  bool); nested objects and missing values are omitted. The account holder's
  full name (`fls_fio`) is exposed as `full_name` (the user opted into all
  non-secret scalar fields for their own instance). The device itself is still
  named after the account/organization, not a person.
- R5 (MUST) Attributes never raise on a partial snapshot.
- R6 (MUST) The previous `period`/`payment_purpose` attributes remain, so
  existing automations keep working.

## Design

- `sensor.py` `DmvlAmountDueSensor.extra_state_attributes` builds the dict
  from `coordinator.data` (Session) and its `personal_account`.
- Money values are floats; `charge_periods`/`payment_count`/`counters`/`receipts`/
  `news` are ints; `unpaid_documents` is a bool.
- The device remains identified by the entry id; the account name is used
  only for the device name.

## API

Entity attribute change only: the balance sensor gains account attributes.
No config, option, service, or unique-id change.

## Test plan

- With the synthetic fixture: the balance sensor exposes the whitelisted
  attributes with expected values, including `full_name` from `fls_fio`;
  `hash` and the password do not appear anywhere in the JSON dump.
- A partial/empty snapshot omits absent attributes and does not raise.
- Money attributes are floats; counts are ints (assert the type, not just the
  value).

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Separate sensors for address/contacts; counters/segments/receipts entities
  (later specs).

## Status

`implemented` (2026-10-02) — the balance sensor exposes the whitelisted account
attributes (identity, address, contacts, service amounts, counts); secrets and
the raw snapshot are not exposed; tests cover present and absent fields.
