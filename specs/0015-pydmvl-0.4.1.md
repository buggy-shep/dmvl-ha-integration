# 0015 — Pin pydmvl 0.4.1

- **Status:** approved
- **Scope:** `dmvl-ha-integration` dependency pin and manifest version

## Summary

`pydmvl` 0.4.1 fixes the `isActual` counter flag parsing (spec 0009 there):
a non-bool encoding (`1`, `"true"`) is no longer read as false. This spec
bumps the exact dependency pin to that release and guards the pins against
drift.

## Motivation

The integration consumes `pydmvl` from PyPI with an exact pin. The 0.4.0 pin
predates the flag-coercion fix, so a service response that encodes the flag as
a number or string could make a meter reading be selected incorrectly.

## Requirements

- R1 (MUST) `custom_components/dmvl/manifest.json` `requirements` pins
  `pydmvl==0.4.1`.
- R2 (MUST) `requirements_dev.txt` pins `pydmvl==0.4.1`.
- R3 (MUST) `manifest.json` `version` is `0.4.2` (the release tag that ships
  this change).
- R4 (MUST) A test asserts the `pydmvl` pin in `manifest.json` equals the pin
  in `requirements_dev.txt` and the installed `pydmvl.__version__`, so a
  version bump cannot forget either file.

## Design

- No runtime code changes: the integration already imports only public
  `pydmvl` names that are unchanged in 0.4.1.
- The guard test reads `manifest.json` and `requirements_dev.txt` and compares
  them with the imported `pydmvl.__version__`.

## API

No entity, service, or config-flow change.

## Test plan

- New `tests/test_manifest.py::test_pydmvl_pin_matches_installed_version`
  (fails before R1–R2, passes after).
- Existing suite (`pytest -m "not live"`, coverage gate) stays green.

## Acceptance criteria

- Gate green (§3/§7); `make ci-ha` (hassfest + hacs/action + tests) green;
  manifest `version` equals the release tag `v0.4.2`.

## Out of scope

- Any change to integration behavior, entities, or options.
- Updating the Home Assistant instance or HACS store in this repository.

## Status

`approved` (2026-10-03: follow-up to `pydmvl` 0.4.1, group conversation).
