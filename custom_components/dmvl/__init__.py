"""The Domovladelets integration (specs 0001-0007).

Setup validates the account by requesting the account snapshot, then keeps a
polling coordinator that feeds the sensor and binary-sensor entities. The
service is stateless (credentials travel with every request), so the account
login and password are stored in the config entry and used to open the
in-memory session; they are never logged. Authentication failures trigger
reauth; connectivity failures retry; unloading closes the client. The
management organization and the account code name the HA device (spec 0011 R4);
an options flow selects the optional entities and the polling interval
(spec 0006); `dmvl.refresh` updates data on demand (spec 0007).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import httpx
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
from pydmvl import ApiError, AsyncDmvlClient, AuthError, Session

from .client import async_new_client
from .const import (
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_VERIFY,
    DEVICE_NAME,
    DOMAIN,
    SERVICE_REFRESH,
    scan_interval_hours,
)
from .coordinator import DmvlDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# The integration is configured only through the UI; `async_setup` exists just
# to register the `dmvl.refresh` service.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DmvlRuntimeData:
    """Per-entry runtime objects (spec 0002 R2, spec 0005)."""

    client: AsyncDmvlClient
    coordinator: DmvlDataUpdateCoordinator
    device_name: str


def account_device_name(session: Session) -> str:
    """HA device name for the account (spec 0005 R1, spec 0011).

    The snapshot name is the management organization, not the account, so the
    account code (login) is appended to keep two accounts of the same
    organization distinguishable: ``<organization> · <login>``.
    """
    organization = session.name
    login = session.login
    if organization and login:
        return f"{organization} · {login}"
    return organization or login or DEVICE_NAME


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

    interval = timedelta(hours=scan_interval_hours(entry.options))
    coordinator = DmvlDataUpdateCoordinator(hass, client, update_interval=interval)
    coordinator.async_set_updated_data(session)
    entry.runtime_data = DmvlRuntimeData(
        client=client,
        coordinator=coordinator,
        device_name=account_device_name(session),
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (spec 0006 R4)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the client (spec 0002 R2)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime: DmvlRuntimeData | None = getattr(entry, "runtime_data", None)
        if runtime is not None:
            await runtime.client.close()
        # Remove the service once no other dmvl entry is loaded (spec 0007 R5).
        # `entry` is still LOADED during this call, so exclude it explicitly.
        others_loaded = any(
            other.entry_id != entry.entry_id and other.state is ConfigEntryState.LOADED
            for other in hass.config_entries.async_entries(DOMAIN)
        )
        if not others_loaded:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the `dmvl.refresh` service (spec 0007 R5)."""

    async def _async_refresh(call: ServiceCall) -> None:
        entry_ids = await async_extract_config_entry_ids(hass, call)
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
            and (not entry_ids or entry.entry_id in entry_ids)
        ]
        for entry in entries:
            runtime: DmvlRuntimeData = entry.runtime_data
            await runtime.coordinator.async_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _async_refresh)
    return True
