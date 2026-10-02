"""Config flow for the Domovladelets integration (spec 0001).

The flow validates the account credentials before creating the entry. Entry
identity is the login normalized with ``strip().lower()``; the login appears in
the entry unique_id, data and title. The password is stored in the entry (the
service is stateless and sends the credentials with every request) and is never
logged. TLS verification is a per-entry option that defaults to disabled.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pydmvl import ApiError, AuthError

from .client import async_new_client
from .const import CONF_LOGIN, CONF_PASSWORD, CONF_VERIFY, DEFAULT_VERIFY, DOMAIN

LOGIN_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
)
PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
)


def normalized_login(login: str) -> str:
    """Entry identity form of a login (spec 0001 R2)."""
    return login.strip().lower()


def _schema(login_default: str | None = None, verify_default: bool = DEFAULT_VERIFY) -> vol.Schema:
    """Build the credential form; the login is prefilled when known."""
    login_key: vol.Marker
    if login_default is None:
        login_key = vol.Required(CONF_LOGIN)
    else:
        login_key = vol.Required(CONF_LOGIN, default=login_default)
    return vol.Schema(
        {
            login_key: LOGIN_SELECTOR,
            vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
            vol.Optional(CONF_VERIFY, default=verify_default): BooleanSelector(),
        }
    )


class DmvlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the account login config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial login step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            await self.async_set_unique_id(normalized_login(login))
            self._abort_if_unique_id_configured()
            error = await self._async_validate(
                login, user_input[CONF_PASSWORD], user_input[CONF_VERIFY]
            )
            if error is not None:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=login,
                    data={
                        CONF_LOGIN: login,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY: user_input[CONF_VERIFY],
                    },
                )
        return self.async_show_form(
            step_id="user", data_schema=_schema(), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after a ConfigEntryAuthFailed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for credentials again and update the existing entry."""
        return await self._async_revalidation_step(
            self._get_reauth_entry(), "reauth_confirm", user_input
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Revalidate the account and update the existing entry."""
        return await self._async_revalidation_step(
            self._get_reconfigure_entry(), "reconfigure", user_input
        )

    async def _async_revalidation_step(
        self,
        entry: ConfigEntry,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Shared reauth/reconfigure form: revalidate, persist, update."""
        schema = _schema(
            entry.data.get(CONF_LOGIN, ""),
            entry.data.get(CONF_VERIFY, DEFAULT_VERIFY),
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            unique_id = normalized_login(login)
            if unique_id != entry.unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
            error = await self._async_validate(
                login, user_input[CONF_PASSWORD], user_input[CONF_VERIFY]
            )
            if error is not None:
                errors["base"] = error
            else:
                data = {
                    CONF_LOGIN: login,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_VERIFY: user_input[CONF_VERIFY],
                }
                if unique_id != entry.unique_id:
                    return self.async_update_reload_and_abort(
                        entry, unique_id=unique_id, title=login, data=data
                    )
                return self.async_update_reload_and_abort(entry, title=login, data=data)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def _async_validate(self, login: str, password: str, verify: bool) -> str | None:
        """Open a session with the real library; return an error base or None.

        The client is always closed, also on failure (spec 0001 R6).
        """
        client = await async_new_client(self.hass, verify=verify)
        try:
            await client.login(login, password)
        except AuthError:
            return "invalid_auth"
        except (ApiError, httpx.HTTPError):
            return "cannot_connect"
        except Exception:  # noqa: BLE001 - surfaced as "unknown"
            return "unknown"
        finally:
            await client.close()
        return None
