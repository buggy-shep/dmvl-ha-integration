"""Setup, unload and refresh tests for the dmvl integration (spec 0002)."""

from __future__ import annotations

import httpx
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.dmvl.const import DOMAIN
from tests.conftest import AccountHandler, make_entry, patch_client

ENTITY_IDS = {
    "sensor.domovladelets_amount_due",
    "sensor.domovladelets_charged",
    "sensor.domovladelets_paid",
    "sensor.domovladelets_last_payment",
    "binary_sensor.domovladelets_unpaid_documents",
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
    assert devices[0].name == "Domovladelets"
    assert devices[0].manufacturer == "Domovladelets"
    assert devices[0].model == "Account"

    for entity_id in ENTITY_IDS:
        assert hass.states.get(entity_id) is not None, entity_id

    entity_registry = er.async_get(hass)
    for entity_id in ENTITY_IDS:
        registry_entry = entity_registry.async_get(entity_id)
        assert registry_entry is not None, entity_id
        assert registry_entry.unique_id.startswith(f"{entry.entry_id}_")


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

    assert float(hass.states.get("sensor.domovladelets_amount_due").state) == 150.0

    handler.payload["personal_account"]["all_debt_c"] = "42.50"
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert float(hass.states.get("sensor.domovladelets_amount_due").state) == 42.5
    assert entry.runtime_data.coordinator.last_update_success is True


async def test_refresh_failure_marks_entities_unavailable(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    handler.transport_error = httpx.ConnectError("refused")
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator.last_update_success is False
    assert hass.states.get("sensor.domovladelets_amount_due").state == "unavailable"


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
