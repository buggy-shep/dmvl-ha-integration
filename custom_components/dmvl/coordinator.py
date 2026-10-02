"""Data update coordinator for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

import logging

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydmvl import ApiError, AsyncDmvlClient, AuthError, Session

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DmvlDataUpdateCoordinator(DataUpdateCoordinator[Session]):
    """Poll the account snapshot and feed the platform entities.

    The client keeps the derived credentials after the initial login, so the
    coordinator only holds the client, never the plaintext password.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: AsyncDmvlClient,
        *,
        update_interval=DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.client = client

    async def _async_update_data(self) -> Session:
        """Fetch a fresh snapshot; map failures to the HA error hierarchy."""
        try:
            return await self.client.fetch()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ApiError, httpx.HTTPError) as err:
            raise UpdateFailed(str(err)) from err
