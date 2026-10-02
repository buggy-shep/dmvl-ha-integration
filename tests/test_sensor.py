"""Sensor tests for the dmvl integration (specs 0002, 0005)."""

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


def _state(hass: HomeAssistant, entry, domain: str, suffix: str):
    return hass.states.get(entity_id(hass, entry, domain, suffix))


async def test_money_sensors(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    assert float(_state(hass, entry, "sensor", "amount_due").state) == 150.0
    assert float(_state(hass, entry, "sensor", "charged").state) == 500.0
    assert float(_state(hass, entry, "sensor", "paid").state) == 350.0

    amount = _state(hass, entry, "sensor", "amount_due")
    assert amount.attributes["device_class"] == "monetary"
    assert amount.attributes["unit_of_measurement"] == "RUB"


async def test_money_sensors_expose_period_and_purpose(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    # distinct dates so the charged/paid override is distinguishable from the
    # account-level fun_date used by amount_due
    payload["personal_account"]["fun_date"] = "2026-09-01"
    payload["history_charges"] = [
        {"ist_date": "2026-07-01", "ist_nach": "100.00", "ist_opl": "50.00"},
        {"ist_date": "2026-09-15", "ist_nach": "250.00", "ist_opl": "100.00"},
    ]
    entry = await _setup(hass, monkeypatch, payload)

    amount = _state(hass, entry, "sensor", "amount_due")
    assert amount.attributes["period"] == "2026-09-01"  # fun_date
    assert amount.attributes["payment_purpose"] == "for utilities"
    # charged/paid report the latest charge period (ist_date), not fun_date
    assert _state(hass, entry, "sensor", "charged").attributes["period"] == "2026-09-15"
    assert _state(hass, entry, "sensor", "paid").attributes["period"] == "2026-09-15"
    assert _state(hass, entry, "sensor", "charged").attributes["payment_purpose"] == "for utilities"


async def test_money_sensors_have_no_cumulative_state_class(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    amount = _state(hass, entry, "sensor", "amount_due")
    assert "state_class" not in amount.attributes


async def test_money_sensors_omit_missing_attributes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"] = {"all_debt_c": "10.00"}
    payload["history_charges"] = []

    entry = await _setup(hass, monkeypatch, payload)

    amount = _state(hass, entry, "sensor", "amount_due")
    assert "period" not in amount.attributes
    assert "payment_purpose" not in amount.attributes


async def test_money_sensors_report_zero_for_absent_aggregates(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"] = {}

    entry = await _setup(hass, monkeypatch, payload)

    assert float(_state(hass, entry, "sensor", "amount_due").state) == 0.0
    assert float(_state(hass, entry, "sensor", "charged").state) == 0.0
    assert float(_state(hass, entry, "sensor", "paid").state) == 0.0
    assert _state(hass, entry, "sensor", "last_payment").state == "unknown"


async def test_last_payment_sensor(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    state = _state(hass, entry, "sensor", "last_payment")
    assert state.state.startswith("2026-09-10")
    assert state.attributes["amount"] == 150.0
    assert state.attributes["device_class"] == "timestamp"


async def test_last_payment_is_unknown_without_payments(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = []

    entry = await _setup(hass, monkeypatch, payload)

    state = _state(hass, entry, "sensor", "last_payment")
    assert state.state == "unknown"
    assert "amount" not in state.attributes


async def test_last_payment_is_unknown_for_unparsable_date(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = [
        {"fo_date": "not-a-date", "fo_sum": "10.00"}
    ]

    entry = await _setup(hass, monkeypatch, payload)

    assert _state(hass, entry, "sensor", "last_payment").state == "unknown"
