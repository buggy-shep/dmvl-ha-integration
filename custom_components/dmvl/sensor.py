"""Sensors for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DmvlRuntimeData
from .const import ATTR_AMOUNT, CURRENCY_RUB
from .coordinator import DmvlDataUpdateCoordinator
from .entity import DmvlEntity

# Read-only state from the shared coordinator; no outbound action.
PARALLEL_UPDATES = 0


class DmvlMoneySensor(DmvlEntity, SensorEntity):
    """Base for the monetary account aggregates (spec 0002 R4)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_RUB
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry, suffix: str
    ) -> None:
        super().__init__(coordinator, entry, suffix)


class DmvlAmountDueSensor(DmvlMoneySensor):
    """The outstanding balance shown as "to pay"."""

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "amount_due")

    @property
    def native_value(self):
        return self.coordinator.data.personal_account.debt_current


class DmvlChargedSensor(DmvlMoneySensor):
    """The total charged for the current period."""

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "charged")

    @property
    def native_value(self):
        return self.coordinator.data.personal_account.charged


class DmvlPaidSensor(DmvlMoneySensor):
    """The total paid for the current period."""

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "paid")

    @property
    def native_value(self):
        return self.coordinator.data.personal_account.paid


class DmvlLastPaymentSensor(DmvlEntity, SensorEntity):
    """Date of the most recent payment, with the amount as an attribute."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_payment")

    @property
    def native_value(self) -> datetime | None:
        payment = self.coordinator.data.last_payment
        if payment is None or not payment.date:
            return None
        parsed = dt_util.parse_date(payment.date)
        if parsed is None:
            return None
        return dt_util.start_of_local_day(parsed)

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        payment = self.coordinator.data.last_payment
        if payment is None:
            return None
        return {ATTR_AMOUNT: float(payment.amount)}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the sensors of a config entry."""
    runtime: DmvlRuntimeData = entry.runtime_data
    coordinator = runtime.coordinator
    async_add_entities(
        [
            DmvlAmountDueSensor(coordinator, entry),
            DmvlChargedSensor(coordinator, entry),
            DmvlPaidSensor(coordinator, entry),
            DmvlLastPaymentSensor(coordinator, entry),
        ]
    )
