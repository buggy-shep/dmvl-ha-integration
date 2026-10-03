"""Binary sensor tests for the dmvl integration (spec 0002)."""

from __future__ import annotations

import copy

import pytest
from homeassistant.core import HomeAssistant

from tests.conftest import (
    AccountHandler,
    entity_id,
    load_fixture,
    make_entry,
    patch_client,
)


async def _setup(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, payload: dict):
    handler = AccountHandler(payload=payload)
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_unpaid_documents_is_on_with_debt(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "on"
    assert state.attributes["device_class"] == "problem"


async def test_unpaid_documents_is_off_when_settled(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "0.00"
    payload["history_charges"] = [
        {
            "ist_date": "2026-09-01",
            "ist_nach": "250.00",
            "ist_nach100": "250.00",
            "ist_opl": "250.00",
        }
    ]

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "off"


async def test_unpaid_documents_is_on_from_signed_balance_only(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The signed balance shows debt even though every period is settled.
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["history_charges"][1]["ist_opl"] = "250.00"

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "on"


async def test_unpaid_documents_is_on_from_unpaid_period_only(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No account-level debt, but one period is not settled.
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "0.00"

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "on"
