"""Sensors for the Domovladelets integration (specs 0002, 0005, 0006)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DmvlRuntimeData
from .const import (
    ATTR_AMOUNT,
    ATTR_DATE,
    ATTR_LAST_PAYMENT_DATE,
    ATTR_PAYMENT_PURPOSE,
    ATTR_PAYMENTS,
    ATTR_PERIOD,
    CURRENCY_RUB,
    OPTION_SHOW_CHARGED,
    OPTION_SHOW_LAST_PAYMENT,
    OPTION_SHOW_PAID,
    option_enabled,
)
from .coordinator import DmvlDataUpdateCoordinator
from .entity import DmvlEntity

# Read-only state from the shared coordinator; no outbound action.
PARALLEL_UPDATES = 0


class DmvlMoneySensor(DmvlEntity, SensorEntity):
    """Base for the monetary account aggregates (spec 0002 R4, 0005 R4).

    The aggregates are per-period values, so no cumulative `state_class` is
    declared.
    """

    _entity_id_domain = Platform.SENSOR
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_RUB

    def __init__(
        self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry, suffix: str
    ) -> None:
        super().__init__(coordinator, entry, suffix)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Account period and payment purpose (spec 0005 R3)."""
        summary = self.coordinator.data.personal_account
        attributes: dict[str, str] = {}
        if summary.period:
            attributes[ATTR_PERIOD] = summary.period
        if summary.payment_purpose:
            attributes[ATTR_PAYMENT_PURPOSE] = summary.payment_purpose
        return attributes or None


class DmvlAccountSensor(DmvlMoneySensor):
    """The account sensor: balance state plus account data (specs 0011, 0010).

    The state is the raw account balance ``all_debt_c``: a negative value is
    the amount to pay (a positive value is an overpayment/credit).
    """

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "account")

    @property
    def native_value(self) -> Decimal:
        return self.coordinator.data.personal_account.debt_current

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Account attributes from the login response (spec 0010 R2)."""
        session = self.coordinator.data
        summary = session.personal_account
        account = session.account
        attributes: dict[str, Any] = {}

        def put(key: str, value: Any) -> None:
            if value is not None and value != "":
                attributes[key] = value

        put("account_code", session.login)
        put("organization", account.organization)
        put("database", account.database)
        put("address", account.address)
        put("flat", account.flat)
        put("management_key", account.management_key)
        put("developer_email", account.developer_email)
        put("contact_email", account.contact_email)
        put("contact_phone", account.phone)
        put("full_name", account.full_name)
        put("period", summary.period)
        put("payment_purpose", summary.payment_purpose)
        put("opening_balance", float(summary.debt_opening))
        put("charged", float(summary.charged))
        put("adjustment", float(summary.difference))
        put("paid", float(summary.paid))
        put("closing_balance", float(summary.debt_closing))
        put("unpaid_documents", session.has_unpaid_documents)
        put("charge_periods", account.charges)
        put("payment_count", account.payments)
        put("counters", account.counters)
        put("receipts", account.receipts)
        put("news", account.news)
        return attributes or None


class DmvlChargedSensor(DmvlMoneySensor):
    """The total charged for the current period."""

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "charged")

    @property
    def native_value(self) -> Decimal:
        return self.coordinator.data.personal_account.charged

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Base attributes plus the latest charge period (spec 0005 R3)."""
        attributes = super().extra_state_attributes or {}
        charges = self.coordinator.data.charges
        if charges and charges[-1].date:
            attributes[ATTR_PERIOD] = charges[-1].date
        return attributes or None


class DmvlPaidSensor(DmvlMoneySensor):
    """The total paid for the current period (spec 0005 R3, spec 0008)."""

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "paid")

    @property
    def native_value(self) -> Decimal:
        return self.coordinator.data.personal_account.paid

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Base attributes, latest charge period and payment rows (0008 R1/R2)."""
        attributes: dict[str, Any] = dict(super().extra_state_attributes or {})
        charges = self.coordinator.data.charges
        if charges and charges[-1].date:
            attributes[ATTR_PERIOD] = charges[-1].date
        payments = self.coordinator.data.personal_account.payments
        if payments:
            attributes[ATTR_PAYMENTS] = [
                {ATTR_DATE: row.date, ATTR_AMOUNT: float(row.amount)} for row in payments
            ]
            latest = payments[-1].date
            # agree with the Last payment sensor: only a parsable date is
            # exposed (spec 0008 R5)
            if latest and dt_util.parse_date(latest) is not None:
                attributes[ATTR_LAST_PAYMENT_DATE] = latest
        return attributes or None


class DmvlLastPaymentSensor(DmvlEntity, SensorEntity):
    """Date of the most recent payment, with the amount as an attribute."""

    _entity_id_domain = Platform.SENSOR
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
    """Create the sensors selected by the options (spec 0002 R4, 0006 R3)."""
    runtime: DmvlRuntimeData = entry.runtime_data
    coordinator = runtime.coordinator
    options = entry.options
    entities: list[SensorEntity] = [DmvlAccountSensor(coordinator, entry)]
    if option_enabled(options, OPTION_SHOW_CHARGED):
        entities.append(DmvlChargedSensor(coordinator, entry))
    if option_enabled(options, OPTION_SHOW_PAID):
        entities.append(DmvlPaidSensor(coordinator, entry))
    if option_enabled(options, OPTION_SHOW_LAST_PAYMENT):
        entities.append(DmvlLastPaymentSensor(coordinator, entry))
    async_add_entities(entities)
