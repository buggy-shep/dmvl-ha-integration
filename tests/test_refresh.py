"""Polling interval and dmvl.refresh service tests (spec 0007)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dmvl.const import (
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    OPTION_SCAN_INTERVAL_HOURS,
    scan_interval_hours,
)
from tests.conftest import AccountHandler, entity_id, make_entry, patch_client


def test_scan_interval_clamps_and_falls_back() -> None:
    assert scan_interval_hours({}) == DEFAULT_SCAN_INTERVAL_HOURS
    assert scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: 0}) == 1
    assert scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: 99}) == 24
    assert scan_interval_hours({OPTION_SCAN_INTERVAL_HOURS: "bad"}) == DEFAULT_SCAN_INTERVAL_HOURS


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
    entry, _ = await _setup(
        hass, monkeypatch, options={OPTION_SCAN_INTERVAL_HOURS: 12}
    )

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


async def test_refresh_service_removed_on_last_unload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await _setup(hass, monkeypatch)
    assert hass.services.has_service(DOMAIN, "refresh")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "refresh")
