"""Data update coordinator for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

import logging

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydmvl import ApiError, AsyncDmvlClient, AuthError, PaymentOptions, Session

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DmvlDataUpdateCoordinator(DataUpdateCoordinator[Session]):
    """Poll the account snapshot and feed the platform entities.

    The client keeps the derived credentials after the initial login, so the
    coordinator only holds the client, never the plaintext password. When the
    due-segments entity is selected, the coordinator also requests the
    ``getpayments`` breakdown on each poll; a non-authentication failure of that
    extra request never fails the account snapshot (spec 0013 R6).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: AsyncDmvlClient,
        *,
        update_interval=DEFAULT_SCAN_INTERVAL,
        include_payment_options: bool = False,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.client = client
        self.include_payment_options = include_payment_options
        self.payment_options: PaymentOptions | None = None

    async def _async_update_data(self) -> Session:
        """Fetch a fresh snapshot; map failures to the HA error hierarchy."""
        try:
            session = await self.client.fetch()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ApiError, httpx.HTTPError) as err:
            raise UpdateFailed(str(err)) from err
        if self.include_payment_options:
            self.payment_options = await self._async_fetch_payment_options()
        else:
            self.payment_options = None
        return session

    async def _async_fetch_payment_options(self) -> PaymentOptions | None:
        """Fetch the amount-due segments without failing the snapshot (R6)."""
        try:
            return await self.client.payment_segments()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ApiError, httpx.HTTPError) as err:
            _LOGGER.warning("amount-due segments are unavailable: %s", err)
            return None
