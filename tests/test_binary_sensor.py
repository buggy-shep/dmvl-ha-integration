"""Binary sensor tests for the dmvl integration (spec 0002, spec 0020)."""

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


async def test_unpaid_documents_is_off_when_period_unsettled_but_no_debt(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0020 R1: no account-level debt, even though one period is not
    # settled (the service allocates payments across periods). The app shows no
    # debt, so the flag is off; the anomaly stays in `unpaid_periods`.
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "0.00"

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "off"
    assert state.attributes["unpaid_periods"] == [
        {"date": "2026-09-01", "charged_adjusted": 250.0, "paid": 100.0}
    ]


async def test_unpaid_periods_empty_when_every_period_settled(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["history_charges"][1]["ist_opl"] = "250.00"

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.attributes["unpaid_periods"] == []


async def test_unpaid_periods_absent_when_no_charges(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0020 R3: with no charges at all the attribute is absent, not empty.
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "0.00"
    payload["history_charges"] = []

    entry = await _setup(hass, monkeypatch, payload)

    state = hass.states.get(entity_id(hass, entry, "binary_sensor", "unpaid_documents"))
    assert state.state == "off"
    assert "unpaid_periods" not in state.attributes
