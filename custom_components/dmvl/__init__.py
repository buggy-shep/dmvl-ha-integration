"""The Domovladelets integration (specs 0001-0003).

Setup validates the account by requesting the account snapshot, then keeps a
polling coordinator that feeds the sensor and binary-sensor entities. The
service is stateless (credentials travel with every request), so the account
login and password are stored in the config entry and used to open the
in-memory session; they are never logged. Authentication failures trigger
reauth; connectivity failures retry; unloading closes the client.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pydmvl import ApiError, AsyncDmvlClient, AuthError, Session

from .client import async_new_client
from .const import CONF_LOGIN, CONF_PASSWORD, CONF_VERIFY
from .coordinator import DmvlDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


@dataclass
class DmvlRuntimeData:
    """Per-entry runtime objects (spec 0002 R2)."""

    client: AsyncDmvlClient
    coordinator: DmvlDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the account from a config entry (spec 0002 R2)."""
    client = await async_new_client(hass, verify=entry.data[CONF_VERIFY])
    try:
        session: Session = await client.login(
            entry.data[CONF_LOGIN], entry.data[CONF_PASSWORD]
        )
    except AuthError as err:
        await client.close()
        raise ConfigEntryAuthFailed(str(err)) from err
    except (ApiError, httpx.HTTPError) as err:
        await client.close()
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = DmvlDataUpdateCoordinator(hass, client)
    coordinator.async_set_updated_data(session)
    entry.runtime_data = DmvlRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the client (spec 0002 R2)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime: DmvlRuntimeData | None = getattr(entry, "runtime_data", None)
        if runtime is not None:
            await runtime.client.close()
    return unload_ok
