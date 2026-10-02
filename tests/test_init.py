"""Setup, unload and refresh tests for the dmvl integration (spec 0002)."""

from __future__ import annotations

import copy

import httpx
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.dmvl.const import DOMAIN
from tests.conftest import (
    LOGIN,
    AccountHandler,
    entity_id,
    load_fixture,
    make_entry,
    patch_client,
)

ENTITY_SUFFIXES = {
    ("sensor", "account"),
    ("sensor", "charged"),
    ("sensor", "paid"),
    ("sensor", "last_payment"),
    ("binary_sensor", "unpaid_documents"),
}


async def test_setup_creates_device_and_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator.data.personal_account.debt_current == 150

    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(devices) == 1
    # device is named after the organization and account code (spec 0011 R1)
    assert devices[0].name == f"Synthetic Housing LLC · {LOGIN}"
    assert devices[0].manufacturer == "Domovladelets"
    assert devices[0].model == "Account"

    entity_registry = er.async_get(hass)
    for domain, suffix in ENTITY_SUFFIXES:
        resolved = entity_id(hass, entry, domain, suffix)
        assert hass.states.get(resolved) is not None, resolved
        registry_entry = entity_registry.async_get(resolved)
        assert registry_entry is not None, resolved
        assert registry_entry.unique_id == f"{entry.entry_id}_{suffix}"


async def test_device_name_falls_back_to_login(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["name"] = ""
    handler = AccountHandler(payload=payload)
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert devices[0].name == LOGIN


async def test_two_entries_get_distinct_device_names(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload_one = copy.deepcopy(load_fixture("authentication.json"))
    payload_one["name"] = "Account One"
    payload_two = copy.deepcopy(load_fixture("authentication.json"))
    payload_two["name"] = "Account Two"
    handler = AccountHandler(
        payload_by_login={LOGIN: payload_one, "other@example.com": payload_two}
    )
    patch_client(monkeypatch, handler)
    first = make_entry(hass)
    second = make_entry(hass, login="other@example.com", unique_id="other@example.com")
    # Setting up the component loads every registered entry for the domain.
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED

    registry = dr.async_get(hass)
    names = {
        dr.async_entries_for_config_entry(registry, e.entry_id)[0].name
        for e in (first, second)
    }
    # each account gets its own device name: organization + account code
    assert names == {
        f"Account One · {LOGIN}",
        "Account Two · other@example.com",
    }


async def test_device_name_falls_back_to_constant(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(payload={**load_fixture("authentication.json"), "name": "", "login": ""})
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, login="")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
    assert devices[0].name == "Domovladelets"


async def test_setup_authentication_failure_triggers_reauth(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_client(monkeypatch, AccountHandler(error="rejected"))
    entry = make_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_setup_transport_failure_retries(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_client(
        monkeypatch, AccountHandler(transport_error=httpx.ConnectError("refused"))
    )
    entry = make_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_unexpected_failure_is_not_a_retry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_client(monkeypatch, AccountHandler(transport_error=RuntimeError("boom")))
    entry = make_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_closes_the_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = entry.runtime_data.client

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert client._client.is_closed


async def test_refresh_updates_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    amount_due = entity_id(hass, entry, "sensor", "account")
    assert float(hass.states.get(amount_due).state) == 150.0

    handler.payload["personal_account"]["all_debt_c"] = "42.50"
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert float(hass.states.get(amount_due).state) == 42.5
    assert entry.runtime_data.coordinator.last_update_success is True


async def test_refresh_failure_marks_entities_unavailable(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    amount_due = entity_id(hass, entry, "sensor", "account")

    handler.transport_error = httpx.ConnectError("refused")
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator.last_update_success is False
    assert hass.states.get(amount_due).state == "unavailable"


async def test_refresh_authentication_failure_starts_reauth(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    handler.error = "rejected"
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator.last_update_success is False
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
