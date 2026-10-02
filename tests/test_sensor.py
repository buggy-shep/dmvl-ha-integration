"""Sensor tests for the dmvl integration (spec 0002)."""

from __future__ import annotations

import copy

import pytest
from homeassistant.core import HomeAssistant

from tests.conftest import AccountHandler, load_fixture, make_entry, patch_client


async def _setup(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, payload: dict):
    handler = AccountHandler(payload=payload)
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_money_sensors(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    assert float(hass.states.get("sensor.domovladelets_amount_due").state) == 150.0
    assert float(hass.states.get("sensor.domovladelets_charged").state) == 500.0
    assert float(hass.states.get("sensor.domovladelets_paid").state) == 350.0

    amount = hass.states.get("sensor.domovladelets_amount_due")
    assert amount.attributes["device_class"] == "monetary"
    assert amount.attributes["unit_of_measurement"] == "RUB"


async def test_money_sensors_report_zero_for_absent_aggregates(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"] = {}

    await _setup(hass, monkeypatch, payload)

    assert float(hass.states.get("sensor.domovladelets_amount_due").state) == 0.0
    assert float(hass.states.get("sensor.domovladelets_charged").state) == 0.0
    assert float(hass.states.get("sensor.domovladelets_paid").state) == 0.0
    assert hass.states.get("sensor.domovladelets_last_payment").state == "unknown"


async def test_last_payment_sensor(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    state = hass.states.get("sensor.domovladelets_last_payment")
    assert state.state.startswith("2026-09-10")
    assert state.attributes["amount"] == 150.0
    assert state.attributes["device_class"] == "timestamp"


async def test_last_payment_is_unknown_without_payments(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = []

    await _setup(hass, monkeypatch, payload)

    state = hass.states.get("sensor.domovladelets_last_payment")
    assert state.state == "unknown"
    assert "amount" not in state.attributes


async def test_last_payment_is_unknown_for_unparsable_date(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = [
        {"fo_date": "not-a-date", "fo_sum": "10.00"}
    ]

    await _setup(hass, monkeypatch, payload)

    assert hass.states.get("sensor.domovladelets_last_payment").state == "unknown"
