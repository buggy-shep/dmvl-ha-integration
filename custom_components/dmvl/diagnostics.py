"""Diagnostics support for the Domovladelets integration (spec 0003)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    ATTR_CHARGED_ADJUSTED,
    ATTR_DATE,
    ATTR_HAS_DEBT,
    ATTR_PAID,
    ATTR_UNPAID_PERIODS,
    CONF_LOGIN,
    CONF_PASSWORD,
    DOMAIN,
)

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
    summary = session.personal_account
    payment = session.last_payment
    diagnostics["account"] = {
        "debt_current": float(summary.debt_current),
        ATTR_HAS_DEBT: summary.has_debt,
        "charged": float(summary.charged),
        "paid": float(summary.paid),
        "has_unpaid_documents": summary.has_debt,
        ATTR_UNPAID_PERIODS: [
            {
                ATTR_DATE: charge.date,
                ATTR_CHARGED_ADJUSTED: float(charge.charged_adjusted),
                ATTR_PAID: float(charge.paid),
            }
            for charge in session.charges
            if not charge.is_paid
        ],
        "last_payment": (
            None
            if payment is None
            else {"date": payment.date, "amount": float(payment.amount)}
        ),
    }
    return diagnostics
