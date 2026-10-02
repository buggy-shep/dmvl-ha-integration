# 0001 — Config flow and account setup

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3)

## Summary

The integration is configured through the Home Assistant UI with the account
login and password. The flow validates the credentials by opening a session
before creating the entry. Entries are keyed by the normalized login; the
login, password, and TLS setting are stored in the entry because the service
is stateless. TLS verification defaults to disabled.

## Motivation

The account must be reachable and the credentials valid before entities exist,
so the integration never shows dead entities. The service may present an
incomplete certificate chain, so the user needs an explicit TLS switch instead
of an unconditional failure.

## Requirements

- R1 (MUST) Config flow steps:
  1. user form: `login` (email text), `password` (masked), `verify` (boolean,
     default `False`);
  2. the integration validates the credentials by requesting the account
     snapshot through `pydmvl`;
  3. success creates a config entry; failure re-shows the form with a typed
     error (`invalid_auth`, `cannot_connect`, `unknown`).
- R2 (MUST) Entry identity: `unique_id` = the login normalized with
  `strip().lower()`. One entry per account; a second login for the same
  normalized login aborts with `already_configured`.
- R3 (MUST) Because the service is stateless (credentials travel with every
  request), `entry.data` holds `login`, `password`, and `verify`. The password
  is Home Assistant storage content (the user's own account, never repository
  content), is never logged, and never appears in diagnostics or test
  fixtures.
- R4 (MUST) Re-authentication: when polling raises an authentication failure
  the entry enters reauth and asks for the password again. A reconfigure step
  revalidates and updates the existing entry in place; both normalize the login
  the same way as the user step and move the `unique_id` when the login
  changes.
- R5 (MUST) TLS option: `verify` is stored in `entry.data` and read by setup.
  The default is `False` (see `pydmvl`): the service may serve an incomplete
  chain.
- R6 (MUST) Error mapping: authentication failure → `invalid_auth`; transport
  and API/protocol failures → `cannot_connect`; anything else → `unknown`. The
  validation client is always closed.

## Design

- The flow builds an `AsyncDmvlClient` (off the event loop; the httpx
  constructor touches the TLS trust store) with `verify` from the form and
  calls `login(login, password)`; a returned snapshot proves the credentials.
- On success the flow stores `login`, `password`, and `verify` in `entry.data`.
  Setup performs its own validation request, so the flow never hands a session
  to setup.
- `config_flow.py` uses HA selectors: `TextSelector(EMAIL)` for the login and
  `TextSelector(PASSWORD)` for the password.
- The options flow is out of scope for this spec; optional settings land with
  the feature that needs them.

## API

- Config flow steps: `user`, `reauth` (+ `reauth_confirm`), `reconfigure`.
- `entry.data` shape: `{"login": str, "password": str, "verify": bool}`.
- `entry.unique_id`: normalized login.

## Test plan

- `pytest-homeassistant-custom-component` fixtures; the real `pydmvl` library
  runs against an `httpx.MockTransport`; no HTTP mocking above the library.
- Happy path creates the entry with `login` + `password` + `verify`; the
  password is present only in `entry.data` (never in logs or diagnostics).
- `invalid_auth`, `cannot_connect`, `unknown`; repeat login aborts with
  `already_configured` for case/whitespace variants.
- Reauth success, reconfigure success, reauth with a changed login, reauth
  onto a taken login.
- Credential selectors: login is an email field, password is masked.

## Acceptance criteria

- Config flow tests green with full `config_flow.py` coverage (bronze rule);
  gate (`pytest -m "not live"`) green; skeptic without `BLOCKING`.

## Out of scope

- Entity behaviour (spec 0002), diagnostics (spec 0003), options flow, meter
  readings, receipt links, any account-changing action.

## Status

`implemented` (phase-3 entry decisions recorded in the group plan,
2026-10-01: minimal entity set, `verify` default `False`, unique_id =
normalized login; implemented 2026-10-02 with the config flow, coordinator and
diagnostics of the first Phase-3 slice).
