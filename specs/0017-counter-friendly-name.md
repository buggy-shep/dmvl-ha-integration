# 0017 — Meter sensor name is "<service> <serial>"

- **Status:** approved
- **Scope:** Home Assistant custom integration `dmvl` (fix for spec 0013 R2)

## Summary

Name each meter sensor after its service and serial
(`"<Counter.service> <Counter.serial>"`) instead of `Counter.name`. The
displayed friendly name is therefore `<device name> <service> <serial>`.

## Motivation

Spec 0013 R2 prefers `Counter.name` (`sch_name`) for the entity name. For real
accounts `sch_name` is often the meter serial (or blank), so the sensor reads
as a bare serial and does not identify the service. `Counter.service`
(`st_name`) plus the serial is the useful, unambiguous label.

## Requirements

- R1 (MUST) The `DmvlCounterSensor` entity name is
  `"<Counter.service> <Counter.serial>"` when both are present (single space,
  no leading/trailing whitespace).
- R2 (MUST) Fallbacks when a part is missing:
  `Counter.service` → `Counter.name` → `Counter.serial`; a name is never empty
  when any of the three fields is set.
- R3 (MUST) Entity ids, unique ids and the entity-id suffix
  (`counter_<slug(serial)>`) are unchanged (specs 0013 R2, 0009).
- R4 (MUST) No other entity, attribute, option or library-pin change.

## Design

- A module-level helper in `sensor.py` builds the name; `DmvlCounterSensor`
  assigns it to `_attr_name`.
- `has_entity_name` remains on, so Home Assistant renders
  `<device name> <entity name>` (specs 0011, 0013 R7).

## API

No new entity, option, service or attribute. The meter sensor's displayed
friendly name changes.

## Test plan

- Fixture meter with name + service + serial → entity name is
  `"<service> <serial>"`.
- Service present without a serial → the bare service; stray whitespace around
  either part is stripped.
- Service missing → `Counter.name`; name and service missing → serial.
- Existing counter tests (state, attributes, entity ids) stay green.

## Acceptance criteria

- Gate green (`pytest -m "not live"`, per-module coverage threshold);
  `make ci-ha` green (hassfest + hacs/action + tests); skeptic without
  `BLOCKING`; released as a patch version.

## Out of scope

- Renaming other entities, changing entity ids, or per-account name templates.

## Status

`approved` (2026-10-03, recorded decision: user requested the meter sensor
friendly name be `"<service> <serial>"`). Supersedes the name clause of spec
0013 R2.
