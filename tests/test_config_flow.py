"""Config flow tests for the dmvl integration (spec 0001).

Every scenario drives the real pydmvl library through an httpx.MockTransport
handler with synthetic fixtures.
"""

from __future__ import annotations

import httpx
import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import BooleanSelector, TextSelector, TextSelectorType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmvl.const import (
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_VERIFY,
    DOMAIN,
)
from tests.conftest import LOGIN, PASSWORD, AccountHandler, patch_client


def field_selector(schema: vol.Schema, key: str):
    """The validator bound to a field of a voluptuous form schema."""
    for marker, validator in schema.schema.items():
        if getattr(marker, "schema", None) == key:
            return validator
    raise AssertionError(f"{key!r} is not present in the schema")


def assert_credential_selectors(schema: vol.Schema) -> None:
    login = field_selector(schema, CONF_LOGIN)
    password = field_selector(schema, CONF_PASSWORD)
    verify = field_selector(schema, CONF_VERIFY)
    assert isinstance(login, TextSelector)
    assert login.config["type"] == TextSelectorType.EMAIL
    assert login.config["autocomplete"] == "username"
    assert isinstance(password, TextSelector)
    assert password.config["type"] == TextSelectorType.PASSWORD
    assert password.config["autocomplete"] == "current-password"
    assert isinstance(verify, BooleanSelector)


async def start_user_flow(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def submit(hass: HomeAssistant, result: dict, data: dict) -> dict:
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    return result


def single_entry(hass: HomeAssistant) -> MockConfigEntry:
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    return entries[0]


async def test_user_form_uses_credential_selectors(hass: HomeAssistant) -> None:
    result = await start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert_credential_selectors(result["data_schema"])


async def test_happy_path_creates_entry_and_loads(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass,
        result,
        {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == LOGIN
    entry = single_entry(hass)
    assert entry.unique_id == LOGIN
    assert entry.data == {
        CONF_LOGIN: LOGIN,
        CONF_PASSWORD: PASSWORD,
        CONF_VERIFY: False,
    }
    assert entry.state is ConfigEntryState.LOADED
    assert handler.requests, "the flow validated the account"


async def test_login_is_normalized_for_unique_id(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass,
        result,
        {
            CONF_LOGIN: "User+Tag@Example.COM ",
            CONF_PASSWORD: PASSWORD,
            CONF_VERIFY: False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = single_entry(hass)
    assert entry.unique_id == "user+tag@example.com"
    assert entry.data[CONF_LOGIN] == "User+Tag@Example.COM"
    assert entry.title == "User+Tag@Example.COM"


async def test_invalid_credentials_shows_invalid_auth(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(error="rejected")
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_unreachable_service_shows_cannot_connect(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(transport_error=httpx.ConnectError("connection refused"))
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_api_error_shows_cannot_connect(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(status=500)
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unexpected_error_shows_unknown(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler(transport_error=RuntimeError("boom"))
    patch_client(monkeypatch, handler)

    result = await start_user_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


@pytest.mark.parametrize("login", [LOGIN, "USER@EXAMPLE.COM", "  user@example.com  "])
async def test_second_login_same_account_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, login: str
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)

    first = await start_user_flow(hass)
    first = await submit(
        hass, first, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )
    assert first["type"] == FlowResultType.CREATE_ENTRY

    second = await start_user_flow(hass)
    second = await submit(
        hass, second, {CONF_LOGIN: login, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )
    assert second["type"] == FlowResultType.ABORT
    assert second["reason"] == "already_configured"


async def make_loaded_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> tuple[MockConfigEntry, AccountHandler]:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=LOGIN,
        data={CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False},
        title=LOGIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, handler


async def test_reauth_form_uses_credential_selectors_and_verifies(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await make_loaded_entry(hass, monkeypatch)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert_credential_selectors(result["data_schema"])

    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.state is ConfigEntryState.LOADED


async def test_reauth_with_invalid_credentials_reshows_form(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await make_loaded_entry(hass, monkeypatch)
    patch_client(monkeypatch, AccountHandler(error="rejected"))

    result = await entry.start_reauth_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: "wrong", CONF_VERIFY: False}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_with_new_login_moves_unique_id(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await make_loaded_entry(hass, monkeypatch)
    patch_client(monkeypatch, AccountHandler())

    result = await entry.start_reauth_flow(hass)
    result = await submit(
        hass,
        result,
        {CONF_LOGIN: "other@example.com", CONF_PASSWORD: PASSWORD, CONF_VERIFY: False},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.unique_id == "other@example.com"
    assert entry.data[CONF_LOGIN] == "other@example.com"


async def test_reauth_to_taken_login_aborts(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = AccountHandler()
    patch_client(monkeypatch, handler)
    entries = []
    for login in (LOGIN, "other@example.com"):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=login,
            data={CONF_LOGIN: login, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False},
            title=login,
        )
        entry.add_to_hass(hass)
        entries.append(entry)
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    reauth_entry = entries[0]
    result = await reauth_entry.start_reauth_flow(hass)
    result = await submit(
        hass,
        result,
        {
            CONF_LOGIN: "other@example.com",
            CONF_PASSWORD: PASSWORD,
            CONF_VERIFY: False,
        },
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def test_reconfigure_flow_updates_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await make_loaded_entry(hass, monkeypatch)
    patch_client(monkeypatch, AccountHandler())

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: True}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_VERIFY] is True
    assert entry.state is ConfigEntryState.LOADED


async def test_reconfigure_with_unreachable_service_reshows_form(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _ = await make_loaded_entry(hass, monkeypatch)
    patch_client(
        monkeypatch,
        AccountHandler(transport_error=httpx.ConnectError("connection refused")),
    )

    result = await entry.start_reconfigure_flow(hass)
    result = await submit(
        hass, result, {CONF_LOGIN: LOGIN, CONF_PASSWORD: PASSWORD, CONF_VERIFY: False}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
