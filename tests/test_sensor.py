"""Sensor tests for the dmvl integration (specs 0002, 0005)."""

from __future__ import annotations

import copy
import json

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dmvl.const import (
    OPTION_SHOW_CHARGE_HISTORY,
    OPTION_SHOW_COUNTERS,
    OPTION_SHOW_DUE_SEGMENTS,
    OPTION_SHOW_RECEIPTS,
)
from tests.conftest import (
    AccountHandler,
    entity_id,
    load_fixture,
    make_entry,
    patch_client,
)


async def _setup(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict,
    options: dict | None = None,
):
    handler = AccountHandler(payload=payload)
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, entry, domain: str, suffix: str):
    return hass.states.get(entity_id(hass, entry, domain, suffix))


async def test_money_sensors(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    assert float(_state(hass, entry, "sensor", "account").state) == -150.0
    assert float(_state(hass, entry, "sensor", "charged").state) == 500.0
    assert float(_state(hass, entry, "sensor", "paid").state) == 350.0

    amount = _state(hass, entry, "sensor", "account")
    assert amount.attributes["device_class"] == "monetary"
    assert amount.attributes["unit_of_measurement"] == "RUB"


async def test_account_sensor_keeps_negative_balance_sign(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "-3148.75"

    entry = await _setup(hass, monkeypatch, payload)

    # the raw reported balance keeps its sign: a negative value is the amount
    # to pay and is not normalized to a positive one (spec 0011 R2)
    assert float(_state(hass, entry, "sensor", "account").state) == -3148.75


async def test_account_unpaid_flag_follows_current_debt(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spec 0020 R2: with no current debt the attribute is False even though a
    # historical period is not settled.
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["all_debt_c"] = "0.00"

    entry = await _setup(hass, monkeypatch, payload)

    attrs = _state(hass, entry, "sensor", "account").attributes
    assert attrs["unpaid_documents"] is False


async def test_account_sensor_exposes_account_attributes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload.update(
        {
            "name": "Synthetic Housing LLC",
            "db": "kp.synthetic",
            "maddr": "Synthetic street, 1",
            "mflat": "  7  ",
            "mgfkey": "<mgfkey>",
            "dev_email": "support@example.invalid",
            "memail": "resident@example.invalid",
            "fls_fio": "<full name>",
            "usersInfo": {"phone": "<phone>", "email": "resident@example.invalid"},
        }
    )
    entry = await _setup(hass, monkeypatch, payload)

    attrs = _state(hass, entry, "sensor", "account").attributes
    assert attrs["account_code"] == "user@example.com"
    assert attrs["organization"] == "Synthetic Housing LLC"
    assert attrs["full_name"] == "<full name>"
    assert attrs["address"] == "Synthetic street, 1"
    assert attrs["flat"] == "7"
    assert attrs["contact_phone"] == "<phone>"
    assert attrs["period"] == "2026-09-01"
    assert isinstance(attrs["charged"], float)
    assert attrs["charged"] == 500.0
    assert isinstance(attrs["paid"], float)
    assert attrs["paid"] == 350.0
    assert attrs["unpaid_documents"] is True
    assert isinstance(attrs["receipts"], int) and not isinstance(attrs["receipts"], bool)
    assert attrs["receipts"] == 1
    # never expose the password, the password hash, or the raw snapshot
    dumped = json.dumps(attrs)
    assert "<hash>" not in dumped
    assert "correct-horse-battery-staple" not in dumped
    assert "raw" not in attrs


async def test_account_sensor_omits_absent_attributes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    for key in ("maddr", "mflat", "dev_email", "usersInfo"):
        payload.pop(key, None)

    entry = await _setup(hass, monkeypatch, payload)

    attrs = _state(hass, entry, "sensor", "account").attributes
    assert "address" not in attrs
    assert "contact_phone" not in attrs


async def test_money_sensors_expose_period_and_purpose(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    # distinct dates so the charged/paid override is distinguishable from the
    # account-level fun_date used by the account sensor
    payload["personal_account"]["fun_date"] = "2026-09-01"
    payload["history_charges"] = [
        {"ist_date": "2026-07-01", "ist_nach": "100.00", "ist_opl": "50.00"},
        {"ist_date": "2026-09-15", "ist_nach": "250.00", "ist_opl": "100.00"},
    ]
    entry = await _setup(hass, monkeypatch, payload)

    amount = _state(hass, entry, "sensor", "account")
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

    amount = _state(hass, entry, "sensor", "account")
    assert "state_class" not in amount.attributes


async def test_money_sensors_omit_missing_attributes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"] = {"all_debt_c": "-10.00"}
    payload["history_charges"] = []

    entry = await _setup(hass, monkeypatch, payload)

    amount = _state(hass, entry, "sensor", "account")
    assert "period" not in amount.attributes
    assert "payment_purpose" not in amount.attributes


async def test_money_sensors_report_zero_for_absent_aggregates(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"] = {}

    entry = await _setup(hass, monkeypatch, payload)

    assert float(_state(hass, entry, "sensor", "account").state) == 0.0
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


async def test_paid_sensor_exposes_payment_dates(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    paid = _state(hass, entry, "sensor", "paid")
    assert paid.attributes["last_payment_date"] == "2026-09-10"
    assert paid.attributes["payments"] == [
        {"date": "2026-08-10", "amount": 200.0},
        {"date": "2026-09-10", "amount": 150.0},
    ]
    # agrees with the Last payment sensor
    last_payment = _state(hass, entry, "sensor", "last_payment")
    assert last_payment.state.startswith(paid.attributes["last_payment_date"])


async def test_paid_sensor_omits_last_date_when_payment_has_no_date(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = [{"fo_sum": "10.00"}]

    entry = await _setup(hass, monkeypatch, payload)

    paid = _state(hass, entry, "sensor", "paid")
    assert "last_payment_date" not in paid.attributes
    assert paid.attributes["payments"] == [{"date": "", "amount": 10.0}]


async def test_paid_sensor_omits_last_date_for_unparsable_date(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = [
        {"fo_date": "not-a-date", "fo_sum": "10.00"}
    ]

    entry = await _setup(hass, monkeypatch, payload)

    paid = _state(hass, entry, "sensor", "paid")
    # agrees with the Last payment sensor, which is unknown for this date
    assert "last_payment_date" not in paid.attributes
    assert _state(hass, entry, "sensor", "last_payment").state == "unknown"


async def test_paid_sensor_omits_payment_attributes_without_payments(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["personal_account"]["payments"] = []

    entry = await _setup(hass, monkeypatch, payload)

    paid = _state(hass, entry, "sensor", "paid")
    assert "last_payment_date" not in paid.attributes
    assert "payments" not in paid.attributes


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


async def test_meter_sensors_expose_reading_and_attributes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        load_fixture("authentication.json"),
        options={OPTION_SHOW_COUNTERS: True},
    )

    water = _state(hass, entry, "sensor", "counter_<meter-1>")
    assert float(water.state) == 124.0
    assert water.attributes["serial"] == "<meter-1>"
    assert water.attributes["service"] == "Cold water meter"
    assert water.attributes["checked"] == "2027-05-01"
    assert water.attributes["volume"] == 4.0
    assert water.attributes["kind"] == "water"
    assert water.attributes["period_start"] == "2026-09-15"
    assert water.attributes["period_end"] == "2026-09-23"
    assert water.attributes["submit_period_start"] == 15
    assert water.attributes["submit_period_end"] == 23
    assert isinstance(water.attributes["submit_period_active"], bool)
    assert water.attributes["is_actual"] is True
    assert len(water.attributes["readings"]) == 2
    assert water.attributes["readings"][-1]["is_actual"] is True

    power = _state(hass, entry, "sensor", "counter_<meter-2>")
    assert float(power.state) == 5500.0
    assert power.attributes["kind"] == "electricity"


async def test_meter_sensor_name_is_service_and_serial(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        load_fixture("authentication.json"),
        options={OPTION_SHOW_COUNTERS: True},
    )

    water = _state(hass, entry, "sensor", "counter_<meter-1>")
    assert water.attributes["friendly_name"].endswith("Cold water meter <meter-1>")
    power = _state(hass, entry, "sensor", "counter_<meter-2>")
    assert power.attributes["friendly_name"].endswith("Electricity meter <meter-2>")


async def test_meter_sensor_name_falls_back_to_name_without_service(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["counters"][0]["st_name"] = None

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    water = _state(hass, entry, "sensor", "counter_<meter-1>")
    assert water.attributes["friendly_name"].endswith("Cold water")


async def test_meter_sensor_name_falls_back_to_serial(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["counters"][0]["st_name"] = None
    payload["counters"][0]["sch_name"] = None

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    water = _state(hass, entry, "sensor", "counter_<meter-1>")
    assert water.attributes["friendly_name"].endswith("<meter-1>")


async def test_meter_sensor_falls_back_to_latest_reading(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    for value in payload["counters"][0]["values"]:
        value["isActual"] = False

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    state = _state(hass, entry, "sensor", "counter_<meter-1>")
    # no reading is marked actual -> the latest period (2026-09-23)
    assert float(state.state) == 124.0
    assert state.attributes["is_actual"] is False
    # the fallback reading's own fields are surfaced too (spec 0014 R3)
    assert state.attributes["volume"] == 4.0
    assert state.attributes["kind"] == "water"
    assert state.attributes["period_end"] == "2026-09-23"


async def test_meter_sensor_prefers_older_actual_over_newer_reading(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["counters"][0]["values"] = [
        {
            "sp_date_b": "2026-09-01",
            "sp_date_e": "2026-09-30",
            "sp_pok": "999.0",
            "sp_val": "1.0",
            "sp_type": "water",
            "isActual": False,
        },
        {
            "sp_date_b": "2026-08-01",
            "sp_date_e": "2026-08-31",
            "sp_pok": "120.0",
            "sp_val": "4.0",
            "sp_type": "water",
            "isActual": True,
        },
    ]

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    state = _state(hass, entry, "sensor", "counter_<meter-1>")
    assert float(state.state) == 120.0
    assert state.attributes["is_actual"] is True
    assert state.attributes["period_end"] == "2026-08-31"


async def test_meter_sensor_picks_latest_regardless_of_order(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    values = payload["counters"][0]["values"]
    for value in values:
        value["isActual"] = False
    values.reverse()

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    assert float(_state(hass, entry, "sensor", "counter_<meter-1>").state) == 124.0


async def test_meter_sensor_unknown_without_readings(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["counters"][0]["values"] = []

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_COUNTERS: True}
    )

    assert _state(hass, entry, "sensor", "counter_<meter-1>").state == "unknown"


async def test_receipts_sensor_lists_links(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        load_fixture("authentication.json"),
        options={OPTION_SHOW_RECEIPTS: True},
    )

    state = _state(hass, entry, "sensor", "receipts")
    assert int(state.state) == 1
    receipts = state.attributes["receipts"]
    assert receipts[0]["kind"] == "utilities"
    assert receipts[0]["name"] == "Receipt"
    assert receipts[0]["link"].startswith("https://")


async def test_receipts_sensor_includes_capital_repair(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = copy.deepcopy(load_fixture("authentication.json"))
    payload["cap_bills"] = [
        {"name": "Capital repair", "link": "https://example.invalid/cap.pdf"}
    ]

    entry = await _setup(
        hass, monkeypatch, payload, options={OPTION_SHOW_RECEIPTS: True}
    )

    receipts = _state(hass, entry, "sensor", "receipts").attributes["receipts"]
    by_kind = {receipt["kind"]: receipt for receipt in receipts}
    assert set(by_kind) == {"utilities", "capital_repair"}
    assert by_kind["capital_repair"]["link"].endswith("cap.pdf")


async def test_counter_entity_ids_are_stable(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        load_fixture("authentication.json"),
        options={OPTION_SHOW_COUNTERS: True},
    )

    water = entity_id(hass, entry, "sensor", "counter_<meter-1>")
    assert water == "sensor.dmvl_user_example_com_counter_meter_1"


async def test_charge_history_sensor_lists_periods(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        load_fixture("authentication.json"),
        options={OPTION_SHOW_CHARGE_HISTORY: True},
    )

    state = _state(hass, entry, "sensor", "charge_history")
    assert int(state.state) == 2
    periods = state.attributes["periods"]
    assert periods[0]["date"] == "2026-08-01"
    assert periods[0]["charged"] == 250.0
    assert periods[0]["is_paid"] is True
    assert periods[1]["paid"] == 100.0
    assert periods[1]["is_paid"] is False


async def test_expansion_entities_absent_by_default(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from homeassistant.helpers import entity_registry as er

    entry = await _setup(hass, monkeypatch, load_fixture("authentication.json"))

    registry = er.async_get(hass)
    unique_ids = {reg.unique_id for reg in registry.entities.values()}
    assert f"{entry.entry_id}_receipts" not in unique_ids
    assert f"{entry.entry_id}_charge_history" not in unique_ids
    assert not any("_counter_" in unique_id for unique_id in unique_ids)


def test_counters_submit_window_helpers() -> None:
    from custom_components.dmvl.const import (
        counters_submit_window,
        submit_window_active,
    )

    assert counters_submit_window(
        {"first_day_counters_values": "15", "last_day_counters_values": "23"}
    ) == (15, 23)
    assert counters_submit_window({}) == (None, None)
    assert submit_window_active(
        {"first_day_counters_values": "15", "last_day_counters_values": "23"}, 20
    ) is True
    assert submit_window_active(
        {"first_day_counters_values": "15", "last_day_counters_values": "23"}, 10
    ) is False
    # a window that wraps the end of the month
    assert submit_window_active(
        {"first_day_counters_values": "25", "last_day_counters_values": "5"}, 2
    ) is True
    assert submit_window_active({}, 2) is None


def test_counter_display_name() -> None:
    from pydmvl import Counter

    from custom_components.dmvl.sensor import _counter_display_name

    def display(
        name: str = "", serial: str = "", service: str | None = None
    ) -> str:
        meter = Counter(
            name=name, serial=serial, service=service, checked=None, readings=()
        )
        return _counter_display_name(meter)

    assert display(serial="42", service="Hot water") == "Hot water 42"
    # stray whitespace is stripped from both parts
    assert display(serial=" 42 ", service=" Hot water ") == "Hot water 42"
    # service without a serial
    assert display(service="Hot water") == "Hot water"
    # service missing -> meter name, then serial
    assert display(name="Meter", serial="42") == "Meter"
    assert display(serial="42") == "42"
    # a whitespace-only name falls through to the serial
    assert display(name="  ", serial="42") == "42"


async def test_due_segments_sensor_from_getpayments(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(
        payload_by_action={"getpayments": load_fixture("getpayments.json")}
    )
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = _state(hass, entry, "sensor", "due_segments")
    assert int(state.state) == 2
    assert state.attributes["text"].startswith("The payment")
    assert state.attributes["hide_sum_with_tax"] is True
    segments = state.attributes["segments"]
    assert segments[0]["payment_id"] == 1
    assert segments[0]["provider"] == "Provider A"
    assert segments[0]["amount"] == 617.28
    assert segments[0]["tax"] == 1.0
    assert segments[0]["tax_amount"] == 617.28


async def test_due_segments_not_requested_when_disabled(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(
        payload_by_action={"getpayments": load_fixture("getpayments.json")}
    )
    patch_client(monkeypatch, handler)
    entry = make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    actions = [request.url.params.get("action") for request in handler.requests]
    assert "getpayments" not in actions


async def test_due_segments_failure_keeps_core_available(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(status_by_action={"getpayments": 500})
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # the account snapshot is still valid and served
    assert float(_state(hass, entry, "sensor", "account").state) == -150.0
    segments = _state(hass, entry, "sensor", "due_segments")
    assert segments.state == "unavailable"


async def test_due_segments_refresh_uses_latest_data(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(
        payload_by_action={"getpayments": load_fixture("getpayments.json")}
    )
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    updated = copy.deepcopy(load_fixture("getpayments.json"))
    updated["count"] = 1
    updated["payments"] = updated["payments"][:1]
    handler.payload_by_action["getpayments"] = updated

    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert int(_state(hass, entry, "sensor", "due_segments").state) == 1


async def test_due_segments_refresh_failure_only_disables_segments(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(
        payload_by_action={"getpayments": load_fixture("getpayments.json")}
    )
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    handler.status_by_action["getpayments"] = 500
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator.last_update_success is True
    assert float(_state(hass, entry, "sensor", "account").state) == -150.0
    assert _state(hass, entry, "sensor", "due_segments").state == "unavailable"


async def test_due_segments_refresh_auth_failure_starts_reauth(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.dmvl.const import DOMAIN

    handler = AccountHandler(
        payload_by_action={"getpayments": load_fixture("getpayments.json")}
    )
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    handler.error_by_action["getpayments"] = "rejected"
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_setup_segments_auth_failure_triggers_reauth(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.dmvl.const import DOMAIN
    from homeassistant.config_entries import ConfigEntryState

    handler = AccountHandler()
    handler.error_by_action["getpayments"] = "rejected"
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, options={OPTION_SHOW_DUE_SEGMENTS: True})

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
