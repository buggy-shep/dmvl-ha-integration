"""Options flow tests for the dmvl integration (spec 0006)."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmvl.const import (
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_VERIFY,
    DOMAIN,
    OPTION_SCAN_INTERVAL_HOURS,
    OPTION_SHOW_CHARGED,
    OPTION_SHOW_LAST_PAYMENT,
    OPTION_SHOW_PAID,
)
from tests.conftest import LOGIN, PASSWORD, AccountHandler, patch_client

OPTIONAL_SUFFIXES = [
    ("sensor", "charged"),
    ("sensor", "paid"),
    ("sensor", "last_payment"),
]
CORE_SUFFIXES = [
    ("sensor", "amount_due"),
    ("binary_sensor", "unpaid_documents"),
]


def _provided(hass: HomeAssistant, entry, domain: str, suffix: str) -> bool:
    """Whether the integration currently provides the entity.

    A disabled entity is removed from the platform: its registry entry may
    remain as a restored ``unavailable`` state, so the live state is checked
    rather than registry presence.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_{suffix}"
    for reg_entry in registry.entities.values():
        if reg_entry.platform == DOMAIN and reg_entry.unique_id == unique_id:
            state = hass.states.get(reg_entry.entity_id)
            return state is not None and state.state != "unavailable"
    return False


async def _setup(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, options=None):
    patch_client(monkeypatch, AccountHandler())
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=LOGIN,
        data={CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False},
        title=LOGIN,
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _submit_options(hass: HomeAssistant, result: dict, data: dict) -> dict:
    result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    return result


async def test_options_form_shows_defaults(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    defaults = {}
    for marker, validator in result["data_schema"].schema.items():
        key = getattr(marker, "schema", None)
        default = marker.default
        defaults[key] = default() if callable(default) else default
    assert defaults[OPTION_SHOW_CHARGED] is True
    assert defaults[OPTION_SHOW_PAID] is True
    assert defaults[OPTION_SHOW_LAST_PAYMENT] is True
    assert defaults[OPTION_SCAN_INTERVAL_HOURS] == 6

    interval_selector = next(
        validator
        for marker, validator in result["data_schema"].schema.items()
        if getattr(marker, "schema", None) == OPTION_SCAN_INTERVAL_HOURS
    )
    config = interval_selector.config
    assert config["min"] == 1
    assert config["max"] == 24


async def test_options_disable_entities_and_reload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(hass, monkeypatch)
    for domain, suffix in OPTIONAL_SUFFIXES + CORE_SUFFIXES:
        assert _provided(hass, entry, domain, suffix), suffix

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await _submit_options(
        hass,
        result,
        {
            OPTION_SHOW_CHARGED: False,
            OPTION_SHOW_PAID: False,
            OPTION_SHOW_LAST_PAYMENT: True,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[OPTION_SHOW_CHARGED] is False
    assert entry.state is ConfigEntryState.LOADED
    # disabled entities are no longer provided by the integration
    assert not _provided(hass, entry, "sensor", "charged")
    assert not _provided(hass, entry, "sensor", "paid")
    assert _provided(hass, entry, "sensor", "last_payment")
    for domain, suffix in CORE_SUFFIXES:
        assert _provided(hass, entry, domain, suffix), suffix


async def test_options_toggle_back_recreates_entities(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = await _setup(
        hass,
        monkeypatch,
        options={
            OPTION_SHOW_CHARGED: False,
            OPTION_SHOW_PAID: False,
            OPTION_SHOW_LAST_PAYMENT: False,
        },
    )
    assert not _provided(hass, entry, "sensor", "charged")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await _submit_options(
        hass,
        result,
        {
            OPTION_SHOW_CHARGED: True,
            OPTION_SHOW_PAID: True,
            OPTION_SHOW_LAST_PAYMENT: True,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    for domain, suffix in OPTIONAL_SUFFIXES:
        assert _provided(hass, entry, domain, suffix), suffix
