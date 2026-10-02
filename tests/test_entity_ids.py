"""Stable entity id tests for the dmvl integration (spec 0009)."""

from __future__ import annotations

import copy

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.conftest import AccountHandler, load_fixture, make_entry, patch_client

EXPECTED_IDS = {
    "sensor.dmvl_user_example_com_account",
    "sensor.dmvl_user_example_com_charged",
    "sensor.dmvl_user_example_com_paid",
    "sensor.dmvl_user_example_com_last_payment",
    "binary_sensor.dmvl_user_example_com_unpaid_documents",
}


async def _setup(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, payload: dict):
    handler = AccountHandler(payload=payload)
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entity_ids_are_login_derived(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    registry = er.async_get(hass)
    ids = {
        reg.entity_id
        for reg in registry.entities.values()
        if reg.platform == "dmvl"
    }
    assert ids == EXPECTED_IDS


async def test_entity_ids_do_not_depend_on_device_name(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["name"] = "A Completely Different Organization Name"

    await _setup(hass, monkeypatch, payload)

    registry = er.async_get(hass)
    ids = {
        reg.entity_id
        for reg in registry.entities.values()
        if reg.platform == "dmvl"
    }
    assert ids == EXPECTED_IDS


async def test_two_accounts_get_distinct_login_derived_ids(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    make_entry(hass)
    make_entry(hass, login="other@example.com", unique_id="other@example.com")
    assert await hass.config_entries.async_setup(
        hass.config_entries.async_entries("dmvl")[0].entry_id
    )
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    ids = {
        reg.entity_id
        for reg in registry.entities.values()
        if reg.platform == "dmvl"
    }
    assert "sensor.dmvl_user_example_com_account" in ids
    assert "sensor.dmvl_other_example_com_account" in ids


async def test_device_identifiers_use_entry_id(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from homeassistant.helpers import device_registry as dr

    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert devices[0].identifiers == {("dmvl", entry.entry_id)}


async def test_entity_ids_fall_back_to_entry_id_for_empty_login(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, login="", unique_id="missing-login")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    ids = {
        reg.entity_id
        for reg in registry.entities.values()
        if reg.platform == "dmvl"
    }
    assert f"sensor.dmvl_{entry.entry_id[:8].lower()}_account" in ids
