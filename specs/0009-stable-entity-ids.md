# 0009 — Stable, account-specific entity ids

- **Status:** implemented
- **Scope:** Home Assistant custom integration `dmvl` (phase 3, third slice)

## Summary

Suggest an explicit, stable entity id `dmvl_<login>_<suffix>` for every entity,
instead of letting Home Assistant derive it from the device name and area.

## Motivation

The device is now named after the account. Entity ids derived from it changed
with the name (and with the area, if the user assigns one), so a rename breaks
automations and "recreate entity ids" produced ids that neither reflect the
account nor stay stable. The reference sibling integration (`danalock`) sets
`entity_id` explicitly from a stable device key; this spec does the same with
the account login.

## Requirements

- R1 (MUST) Each entity suggests `entity_id = <platform>.dmvl_<login-slug>_<suffix>`,
  where the platform is `sensor`/`binary_sensor`, `<login-slug>` is the config
  entry login through `slugify`, and `<suffix>` is the entity's translation key.
- R2 (MUST) The slug is derived from the login only, never from the device
  name or the area, so the id is stable across device renames and area
  changes. When the login slugs to empty or to `"unknown"` (Home Assistant's
  slugify result for punctuation-only input), `entry_id[:8]` is used instead.
- R3 (MUST) The device `unique_id` stays `f"{entry.entry_id}_{suffix}"` (entity
  identity), and the device registry identifiers stay `(DOMAIN, entry_id)`, so
  no account data reaches the registry.
- R4 (MUST) The change is additive: an existing registry entry keeps its
  current entity id; the suggestion applies to newly registered entities.
- R5 (MUST) `has_entity_name` and translation keys are unchanged, so friendly
  names still come from the account-named device.

## Design

- `entity.py` sets `self.entity_id` in `DmvlEntity.__init__` from
  `_entity_id_domain` (set by each platform base class) and the slugified login.
- No migration of existing entity ids is performed (R4); users can rename in
  the UI if desired.

## API

Entity-id suggestion change only. No config, option, service, or unique-id
change.

## Test plan

- Register an account: the entity ids are exactly
  `sensor.dmvl_<login-slug>_amount_due` (and siblings), independent of the
  device name; churn the snapshot name and confirm the ids do not change.
- Two accounts get different, login-derived ids.
- Unique ids and device identifiers remain entry-based.

## Acceptance criteria

- Tests green with full coverage; gate green; skeptic without `BLOCKING`.

## Out of scope

- Migrating ids of already-registered entities (HA forbids changing unique_id;
  entity_id is user-editable).

## Status

`implemented` (2026-10-02) — entity ids are suggested as
`<platform>.dmvl_<login>_<suffix>`, independent of the device name and area.
