"""Diagnostics support for the Domovladelets integration (spec 0003)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CONF_LOGIN, CONF_PASSWORD, DOMAIN

TO_REDACT = {CONF_LOGIN, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return a redacted snapshot of the entry and the account aggregates."""
    integration = await async_get_integration(hass, DOMAIN)
    diagnostics: dict[str, Any] = {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "version": integration.version,
        },
        "account": None,
    }

    runtime = getattr(entry, "runtime_data", None)
    if runtime is None:
        return diagnostics

    session = runtime.coordinator.data
    payment = session.last_payment
    diagnostics["account"] = {
        "debt_current": float(session.personal_account.debt_current),
        "charged": float(session.personal_account.charged),
        "paid": float(session.personal_account.paid),
        "has_unpaid_documents": session.has_unpaid_documents,
        "last_payment": (
            None
            if payment is None
            else {"date": payment.date, "amount": float(payment.amount)}
        ),
    }
    return diagnostics
