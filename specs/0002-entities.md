# 0002 — Coordinator and entities

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3)

## Summary

One `DataUpdateCoordinator` polls the account snapshot and feeds a minimal set
of entities: the account balance aggregates, a binary sensor for unpaid
documents, and the latest payment. All values are read-only.

## Motivation

The whole account screen arrives in a single request, so one coordinator per
account is enough. A minimal default set keeps the integration useful without
flooding the entity registry; the broader set (meter readings, per-segment
amounts, receipt links) is deferred to later specs.

## Requirements

- R1 (MUST) A `DataUpdateCoordinator[Session]` holds the latest snapshot and
  polls on an interval (default: 1 hour). The first fetch happens during setup
  and is the connection test (`test-before-setup`).
- R2 (MUST) Setup: build the client off the event loop, call `login`, and map
  failures: authentication → `ConfigEntryAuthFailed`; transport/API → 
  `ConfigEntryNotReady`. Any other exception propagates (it is a bug, not a
  transient condition). `entry.runtime_data` holds the client and coordinator;
  `async_unload_entry` closes the client.
- R3 (MUST) Exactly one HA device per config entry, identified by
  `(DOMAIN, entry.entry_id)`, manufacturer `Domovladelets`, model `Account`.
  The device name was a fixed constant in this spec; it is now derived from
  the account (see spec 0005 R1 and spec 0011 R1, which supersede this point).
- R4 (MUST) Entities (per account), all `has_entity_name` with stable unique
  ids `f"{entry.entry_id}_{suffix}"` and device info from R3:
  - `sensor` **Account** = `personal_account.debt_current` as reported
    (negative = to pay, positive = overpayment), monetary (RUB);
  - `sensor` **Charged** = `personal_account.charged`, monetary (RUB);
  - `sensor` **Paid** = `personal_account.paid`, monetary (RUB);
  - `binary_sensor` **Unpaid documents** = `Session.has_unpaid_documents`,
    device class `problem`;
  - `sensor` **Last payment** = the date of `Session.last_payment` (timestamp),
    with the amount as an attribute.
- R5 (MUST) All entities are `CoordinatorEntity` subclasses: they report
  `available` from the coordinator and update on coordinator refreshes
  (`entity-event-setup`).
- R6 (MUST) Read-only: `PARALLEL_UPDATES = 0`; no outbound action beyond the
  periodic poll.
- R7 (MUST) A missing last payment renders as `unknown` and never raises. The
  library maps absent account aggregates to `Decimal(0)`, so the money sensors
  report `0` for an absent scalar rather than `unknown`; that behavior is
  accepted and recorded here.
- R8 (MUST) On a refresh failure the coordinator raises `UpdateFailed`; an
  authentication failure raises `ConfigEntryAuthFailed` (reauth).

## Design

- `coordinator.py` wraps `AsyncDmvlClient`. Setup calls `login` with the stored
  login/password (this is the connection test); later updates call `fetch`.
  Because the client keeps the derived credentials after the first login, the
  coordinator stores only the client, not the password.
- Setup order: build client (executor) → `client.login` (this is the
  connection test) → coordinator seeded with `async_set_updated_data(session)`
  → forward platforms. No separate `async_config_entry_first_refresh()` is
  issued, so setup makes exactly one request. `runtime_data` is a dataclass
  `DmvlRuntimeData(client, coordinator)`.
- Entities read `coordinator.data` (a `pydmvl.models.Session`). Monetary values
  are `Decimal` and rendered as-is. The last-payment sensor uses
  `SensorDeviceClass.TIMESTAMP` and exposes `{"amount": ...}` as attributes.
- The device name is the account name (superseded details: spec 0005 added the
  account-derived name; spec 0011 makes it `<organization> · <login>`);
  per-entry uniqueness comes from the identifiers.

## API

- `entry.runtime_data`: `DmvlRuntimeData(client: AsyncDmvlClient,
  coordinator: DmvlDataUpdateCoordinator)`.
- Platforms: `sensor`, `binary_sensor`.

## Test plan

- Synthetic `authentication` fixture driven through `httpx.MockTransport`
  against the real `pydmvl` parser.
- Setup creates one device, one coordinator, and the expected entities with
  `{entry.entry_id}_{suffix}` unique ids; unload closes the client.
- State assertions for each entity (including the empty-payment case → 
  `unknown`).
- Auth failure during setup → `ConfigEntryAuthFailed`; transport failure → 
  `ConfigEntryNotReady`.
- Refresh failure → entities become unavailable; auth failure → reauth.

## Acceptance criteria

- Entity/state tests and init tests green; gate green; skeptic without
  `BLOCKING`.

## Out of scope

- Meter readings, per-segment amounts, receipt links, historical periods,
  options flow, changing actions.

## Status

`implemented` (phase-3 entry decisions recorded in the group plan, 2026-10-01,
including the minimal default set and the fixed device name; implemented
2026-10-02 as the first Phase-3 slice). The **Amount due** sensor was renamed to
**Account** and its device name and balance semantics were refined by spec 0011
(`<organization> · <login>`, raw sign), after spec 0010 added the account
attributes; this spec's R3/R4 statements on the name and sensor are superseded
where they conflict.
