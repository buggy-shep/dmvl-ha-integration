"""Diagnostics tests for the dmvl integration (spec 0003)."""

from __future__ import annotations

import json

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dmvl.diagnostics import async_get_config_entry_diagnostics
from tests.conftest import (
    LOGIN,
    PASSWORD,
    AccountHandler,
    make_entry,
    patch_client,
)


async def test_diagnostics_redacts_credentials(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert str(result["entry"]["version"]) == "0.2.1"
    assert result["account"]["debt_current"] == 150.0
    assert result["account"]["charged"] == 500.0
    assert result["account"]["paid"] == 350.0
    assert result["account"]["has_unpaid_documents"] is True
    assert result["account"]["last_payment"] == {"date": "2026-09-10", "amount": 150.0}

    dumped = json.dumps(result)
    assert LOGIN not in dumped
    assert PASSWORD not in dumped


async def test_diagnostics_without_runtime_data(
    hass: HomeAssistant,
) -> None:
    entry = make_entry(hass)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["account"] is None
    assert result["entry"]["data"]["login"] == "**REDACTED**"
    assert result["entry"]["data"]["password"] == "**REDACTED**"
