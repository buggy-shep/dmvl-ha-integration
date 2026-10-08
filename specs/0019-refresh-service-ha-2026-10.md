# 0019 — `dmvl.refresh` survives the Home Assistant service-target helper change

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (fix)
- **Supersedes:** nothing; complements spec 0012 R1–R3

## Summary

Make the `dmvl.refresh` service work when Home Assistant changes the
`async_extract_config_entry_ids` helper from a `hass`-first signature to a
`ServiceCall`-first one (observed on HA 2026.10.0). The integration adapts to
either signature instead of pinning a hard minimum core version.

## Motivation

On HA 2026.10.0 `dmvl.refresh` answers HTTP 500. In 2026.10.0 the helper is
called as `async_extract_config_entry_ids(service_call, expand_group=True)` and
uses `service_call.hass` internally; the integration still calls
`async_extract_config_entry_ids(hass, call)`, so `hass` lands in the
`service_call` parameter and `hass.hass` raises `AttributeError`
(`custom_components/dmvl/__init__.py`, `_async_refresh`). The regression was not
caught because the test environment pins an older Home Assistant
(`pytest-homeassistant-custom-component==0.13.205` → HA 2025.1.4) whose helper
still takes `hass` first.

A hard minimum-version bump to 2026.10.0 was considered and rejected: HA
2026.10 requires Python >= 3.14, which is not available in this workspace (only
3.12.3) and Docker/`act` is unavailable, so the mandatory local-green gate
could not be run against it; the bump would also drop users on older cores
unnecessarily. Adapting to the signature is small, verifiable against the
pinned core, and keeps the supported range wide.

## Requirements

- R1 (MUST) The refresh handler extracts config entry ids successfully on both
  helper signatures: `hass`-first (`(hass, service_call, expand_group)`) and
  `ServiceCall`-first (`(service_call, expand_group)`). No `AttributeError` on
  either.
- R2 (MUST) The service behavior is unchanged: without a target it refreshes
  every loaded `dmvl` entry; with an entity/device target it refreshes the
  owning entry(ies); it stays read-only (spec 0012 R3).
- R3 (MUST) No hard minimum-core bump and no change to `requirements_dev.txt`,
  the CI Python version, or `hacs.json` are required to ship this fix.
- R4 (SHOULD) The signature adaptation is a single, documented helper with a
  clear comment, so the reason survives the next core change.

## Design

- `__init__.py`: add a small helper used by `_async_refresh`:

  ```python
  async def _async_extract_entry_ids(
      hass: HomeAssistant, call: ServiceCall
  ) -> set[str]:
      params = inspect.signature(async_extract_config_entry_ids).parameters
      if next(iter(params), None) == "hass":
          return await async_extract_config_entry_ids(hass, call)
      return await async_extract_config_entry_ids(call)
  ```

- Detection keys on the `bind_hass` contract: a `hass`-first helper declares a
  leading `hass` parameter; after the core refactor the leading parameter is
  `service_call`. The helper is resolved at call time so the branch is
  exercisable in a test by substituting the imported name.
- The `hass` argument stays in the signature even in the new branch (where it
  is unused) so the call site and the tests are identical across branches; a
  lint suppression is avoided by keeping the parameter referenced in the
  `hass`-first branch.

## API

No user-facing API change. `dmvl.refresh` keeps its name, target schema
(`services.yaml`) and read-only behavior.

## Test plan

- Existing spec 0007/0012 refresh tests stay green (they exercise the
  `hass`-first helper present in the pinned environment).
- New test: replace `custom_components.dmvl.async_extract_config_entry_ids`
  with a stub carrying the new `(service_call, expand_group=True)` signature
  that asserts its first argument is the `ServiceCall` and returns a known
  entry id; the targeted `dmvl.refresh` call must refresh only that entry and
  not raise. This test fails before the fix and passes after it.
- New test: an untargeted call still refreshes every loaded entry under the
  adapted helper.

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Running the suite against a real HA 2026.10.0 (HA 2026.10 requires Python
  >= 3.14, unavailable in this workspace; the signature adaptation is covered
  by a simulated helper).
- Lowering the pinned Home Assistant version or removing the adaptation once
  the whole supported range uses the new signature (a future cleanup).

## Status

`approved` (2026-10-08) — recorded user decision to fix the reported 2026.10.0
refresh failure in a single branch/PR together with spec 0020.
