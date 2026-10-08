"""Binary sensors for the Domovladelets integration (spec 0002, spec 0020)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DmvlRuntimeData
from .const import (
    ATTR_CHARGED_ADJUSTED,
    ATTR_DATE,
    ATTR_PAID,
    ATTR_UNPAID_PERIODS,
)
from .entity import DmvlEntity

# Read-only state from the shared coordinator; no outbound action.
PARALLEL_UPDATES = 0


class DmvlUnpaidDocumentsBinarySensor(DmvlEntity, BinarySensorEntity):
    """On when the account currently owes money (spec 0020 R1/R3).

    The state follows the signed current balance (``debt_current < 0``), which
    matches the vendor app, rather than the unreliable per-period "any charge
    unpaid" rule (payments are allocated across periods). The per-period
    anomaly stays visible in the ``unpaid_periods`` attribute.
    """

    _entity_id_domain = Platform.BINARY_SENSOR
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "unpaid_documents")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.personal_account.has_debt

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """The unsettled periods behind the flag, or ``None`` without charges."""
        charges = self.coordinator.data.charges
        if not charges:
            return None
        return {
            ATTR_UNPAID_PERIODS: [
                {
                    ATTR_DATE: charge.date,
                    ATTR_CHARGED_ADJUSTED: float(charge.charged_adjusted),
                    ATTR_PAID: float(charge.paid),
                }
                for charge in charges
                if not charge.is_paid
            ]
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the binary sensors of a config entry."""
    runtime: DmvlRuntimeData = entry.runtime_data
    async_add_entities([DmvlUnpaidDocumentsBinarySensor(runtime.coordinator, entry)])
