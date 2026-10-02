"""Shared fixtures for the dmvl integration tests.

All fixture data is synthetic. The real `pydmvl` library runs against an
`httpx.MockTransport`; there is no HTTP mocking above the library boundary.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dmvl.const import (
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_VERIFY,
    DOMAIN,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

LOGIN = "user@example.com"
PASSWORD = "correct-horse-battery-staple"


def load_fixture(name: str) -> Any:
    """Load a synthetic API fixture by file name."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class AccountHandler:
    """httpx.MockTransport handler emulating the account service.

    Scenarios are configured through attributes; tests may mutate them between
    requests (for example to make a later poll fail).
    """

    def __init__(
        self,
        *,
        status: int = 200,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
        transport_error: Exception | None = None,
    ) -> None:
        self.status = status
        self.payload = payload if payload is not None else load_fixture("authentication.json")
        self.error = error
        self.transport_error = transport_error
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.transport_error is not None:
            raise self.transport_error
        if self.error is not None:
            return httpx.Response(200, json={"error": self.error})
        return httpx.Response(self.status, json=self.payload)


def patch_client(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    """Route clients built by the integration through the mock transport.

    `async_new_client` resolves the class from the `client` module at call
    time, so patching that module attribute covers setup and the config flow.
    """
    from custom_components.dmvl import client as client_module

    real = client_module.AsyncDmvlClient

    def factory(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return real(*args, **kwargs)

    monkeypatch.setattr(client_module, "AsyncDmvlClient", factory)


def make_entry(
    hass: HomeAssistant,
    *,
    login: str = LOGIN,
    password: str = PASSWORD,
    verify: bool = False,
    unique_id: str | None = None,
) -> MockConfigEntry:
    """Create and register a dmvl config entry for the account."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=unique_id if unique_id is not None else login.strip().lower(),
        data={CONF_LOGIN: login, CONF_PASSWORD: password, CONF_VERIFY: verify},
        title=login,
    )
    entry.add_to_hass(hass)
    return entry


async def setup_entry(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    handler: AccountHandler,
    *,
    login: str = LOGIN,
    password: str = PASSWORD,
    verify: bool = False,
) -> MockConfigEntry:
    """A dmvl entry set up against the mock handler."""
    patch_client(monkeypatch, handler)
    entry = make_entry(hass, login=login, password=password, verify=verify)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration in every test."""
    yield
