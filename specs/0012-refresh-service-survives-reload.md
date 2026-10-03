# 0012 — Refresh service survives a config entry reload

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, fourth slice)

## Summary

Keep the `dmvl.refresh` service registered across a config entry reload
(options change, `homeassistant.reload_config_entry`, reauth/reconfigure). The
service is registered once per loaded entry and is no longer removed while an
entry remains loaded.

## Motivation

Spec 0007 registered `dmvl.refresh` in `async_setup` and removed it in
`async_unload_entry` when the last entry unloaded. Home Assistant does **not**
re-run `async_setup` (the component setup) when it reloads a config entry: a
reload unloads the entry — which removes the service — and loads it again
without a second `async_setup`. The service therefore disappears until a full
core restart whenever an entry is reloaded (for example after an options
change, or via the `homeassistant.reload_config_entry` action used as an
automation workaround). This was observed live: the domain vanished from
`/api/services` and `dmvl.refresh` answered HTTP 400 while the entry was
`loaded`. Scheduling `dmvl.refresh` from an automation then fails.

## Requirements

- R1 (MUST) The `dmvl.refresh` service is registered when a `dmvl` config entry
  is set up and **stays registered** while at least one entry is loaded,
  including across a reload (`async_reload` / `homeassistant.reload_config_entry`
  / options-change reload).
- R2 (MUST) Registration is idempotent: setting up or reloading a second entry
  must not raise or overwrite the service in a way that breaks it.
- R3 (MUST) The service keeps its behavior: without a target it refreshes every
  loaded `dmvl` entry; with an entity/device target it refreshes the owning
  entry(ies). It remains read-only.
- R4 (MUST) The service is no longer removed in `async_unload_entry`. The
  domain service persists even after the last config entry is removed, until
  Home Assistant shuts down (HA does not unregister a `hass.services`
  registration when a config entry unloads). A lingering service on zero
  entries is safe because the handler iterates loaded entries only, so a call
  is an inert no-op rather than an error.
- R5 (MUST) Spec 0007 R5 is superseded on this point: the "removed in
  `async_unload_entry`" clause is replaced by the registration in
  `async_setup_entry`. All other spec 0007 requirements stand.

## Design

- `__init__.py`: move service registration from `async_setup` into
  `async_setup_entry`, guarded by `hass.services.has_service(DOMAIN,
  SERVICE_REFRESH)` (idempotent). Keep the handler as a shared function;
  `async_setup` keeps only the `CONFIG_SCHEMA` (config-entry-only) declaration.
- `async_unload_entry`: drop the `async_remove` block and the now-unused
  `ConfigEntryState` bookkeeping for the service; still close the client.
- Rationale: Home Assistant quality scale expects a shared integration service
  to be registered once for the component and not torn down on entry unload;
  an entry-scoped service must survive reloads to remain callable by
  automations.

## API

No user-facing API change: `dmvl.refresh` keeps its name, target schema
(`services.yaml`) and read-only behavior. The effect is that it no longer
vanishes after a reload.

## Test plan

- Reload the entry (`hass.config_entries.async_reload`): the service is still
  registered and a `dmvl.refresh` call still succeeds afterwards.
- Unload the last entry: unlike the old behavior, the service stays registered
  and a call is inert (no loaded entries to refresh, no error).
- With two entries, reloading one keeps the service and still refreshes the
  other on an untargeted call.
- Existing spec 0007 refresh tests remain green (adjust the removal test).

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Unregistering a service at shutdown explicitly (HA clears `hass.services` on
  stop).
- The `homeassistant.reload_config_entry` service itself (HA removes that in
  2026.3); this spec only removes the dependency on it for `dmvl.refresh`.

## Status

`approved` (2026-10-03) — fix registered before merge; supersedes spec 0007 R5
on service removal.
