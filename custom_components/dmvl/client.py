"""Client construction for the Domovladelets integration.

The httpx client constructor loads the TLS trust store synchronously, which
Home Assistant flags as a blocking call inside the event loop; the client is
therefore built in the executor. All construction goes through
:func:`async_new_client` so tests have a single injection point.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pydmvl import AsyncDmvlClient


async def async_new_client(hass: HomeAssistant, *, verify: bool) -> AsyncDmvlClient:
    """Build an asynchronous account client off the event loop."""

    def _build() -> AsyncDmvlClient:
        return AsyncDmvlClient(verify=verify)

    return await hass.async_add_executor_job(_build)
