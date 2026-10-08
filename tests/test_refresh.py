"""Polling interval and dmvl.refresh service tests (spec 0007)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.dmvl.const import (
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    OPTION_SCAN_INTERVAL_HOURS,
    scan_interval_hours,
)
from tests.conftest import (
    AccountHandler,
    entity_id,
    load_fixture,
    make_entry,
    patch_client,
)


def test_scan_interval_clamps_and_falls_back() -> None:
    assert scan_interval_hours({}) == DEFAULT_SCAN_INTERVAL_HOURS
    assert scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: 0}) == 1
    assert scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: 99}) == 24
    assert (
        scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: "bad"})
        == DEFAULT_SCAN_INTERVAL_HOURS
    )


async def _setup(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, options=None):
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, handler


async def test_default_interval_is_six_hours(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await _setup(hass, monkeypatch)

    assert entry.runtime_data.coordinator.update_interval == timedelta(
        hours=DEFAULT_SCAN_INTERVAL_HOURS
    )


async def test_configured_interval_is_honored(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await _setup(hass, monkeypatch, options={OPTION_SCAN_INTERVAL_HOURS: 12})

    assert entry.runtime_data.coordinator.update_interval == timedelta(hours=12)


async def test_refresh_service_without_target_refreshes_all(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, handler = await _setup(hass, monkeypatch)
    requests_before = len(handler.requests)

    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()

    assert len(handler.requests) > requests_before
    assert entry.runtime_data.coordinator.last_update_success is True


async def test_refresh_service_with_entity_target(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, handler = await _setup(hass, monkeypatch)
    amount_due = entity_id(hass, entry, "sensor", "account")
    requests_before = len(handler.requests)

    await hass.services.async_call(
        DOMAIN, "refresh", {"entity_id": amount_due}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(handler.requests) > requests_before


async def test_refresh_service_survives_entry_reload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression (spec 0012): a reload does not re-run async_setup, so a service
    # removed in async_unload_entry would vanish. It must stay registered.
    entry, handler = await _setup(hass, monkeypatch)
    assert hass.services.has_service(DOMAIN, "refresh")

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "refresh")
    requests_before = len(handler.requests)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()
    assert len(handler.requests) > requests_before


async def test_refresh_service_is_registered_once_for_two_entries(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0012 R2: registering a second entry must be idempotent (no raise,
    # one surviving service that still refreshes both entries).
    handler = AccountHandler(
        payload_by_login={
            "user@example.com": load_fixture("authentication.json"),
            "other@example.com": load_fixture("authentication.json"),
        }
    )
    patch_client(monkeypatch, handler)
    first = make_entry(hass)
    second = make_entry(hass, login="other@example.com", unique_id="other@example.com")
    # Setting up the component loads every registered entry for the domain.
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED

    assert hass.services.has_service(DOMAIN, "refresh")
    requests_before = len(handler.requests)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()
    assert len(handler.requests) >= requests_before + 2
    assert first.runtime_data.coordinator.last_update_success is True
    assert second.runtime_data.coordinator.last_update_success is True


async def test_reloading_one_of_two_entries_keeps_service_and_refreshes_both(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0012 test plan: reload one entry of two; the service survives and an
    # untargeted call still refreshes both loaded entries.
    handler = AccountHandler(
        payload_by_login={
            "user@example.com": load_fixture("authentication.json"),
            "other@example.com": load_fixture("authentication.json"),
        }
    )
    patch_client(monkeypatch, handler)
    first = make_entry(hass)
    second = make_entry(hass, login="other@example.com", unique_id="other@example.com")
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_reload(first.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "refresh")

    requests_before = len(handler.requests)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()
    # untargeted call refreshes both loaded entries
    assert len(handler.requests) >= requests_before + 2
    assert first.runtime_data.coordinator.last_update_success is True
    assert second.runtime_data.coordinator.last_update_success is True


async def test_refresh_service_kept_after_last_unload_and_inert(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0012 R4: the service is no longer removed on entry unload; an
    # untargeted call with no loaded entry is a harmless no-op.
    entry, handler = await _setup(hass, monkeypatch)
    assert hass.services.has_service(DOMAIN, "refresh")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "refresh")
    requests_before = len(handler.requests)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()
    assert len(handler.requests) == requests_before


async def test_refresh_service_adapts_to_service_call_first_helper(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0019: HA 2026.10.0 changed async_extract_config_entry_ids to take the
    # ServiceCall first. The integration must detect the signature and pass the
    # ServiceCall, not hass (which raised AttributeError: no attribute 'hass').
    entry, handler = await _setup(hass, monkeypatch)
    seen: list[ServiceCall] = []

    async def _service_call_first(service_call, expand_group=True):
        # Mirror the 2026.10 helper, which reads ``service_call.hass``. The
        # pre-fix call passed ``hass`` as the first argument, so this raises
        # AttributeError before the fix and succeeds after it.
        assert service_call.hass is hass
        seen.append(service_call)
        return {entry.entry_id}

    monkeypatch.setattr(
        "custom_components.dmvl.async_extract_config_entry_ids",
        _service_call_first,
    )

    requests_before = len(handler.requests)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()

    assert len(seen) == 1
    assert isinstance(seen[0], ServiceCall)
    assert len(handler.requests) > requests_before
    assert entry.runtime_data.coordinator.last_update_success is True
