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
from homeassistant.util import slugify
from pydmvl import Counter, CounterReading

from . import DmvlRuntimeData
from .const import (
    ATTR_AMOUNT,
    ATTR_BENEFIT,
    ATTR_BUTTON,
    ATTR_CHARGED,
    ATTR_CHARGED_ADJUSTED,
    ATTR_CHECKED,
    ATTR_DATE,
    ATTR_DEBT_CLOSING,
    ATTR_DEBT_OPENING,
    ATTR_DIFFERENCE,
    ATTR_HIDE_SUM_WITH_TAX,
    ATTR_INPUT,
    ATTR_IS_ACTUAL,
    ATTR_IS_PAID,
    ATTR_KIND,
    ATTR_LAST_PAYMENT_DATE,
    ATTR_LINK,
    ATTR_NAME,
    ATTR_PAID,
    ATTR_PAYMENT_ID,
    ATTR_PAYMENT_PURPOSE,
    ATTR_PAYMENTS,
    ATTR_PERIOD,
    ATTR_PERIOD_END,
    ATTR_PERIOD_START,
    ATTR_PERIODS,
    ATTR_PROVIDER,
    ATTR_READINGS,
    ATTR_READING,
    ATTR_RECEIPTS,
    ATTR_SEGMENTS,
    ATTR_SERIAL,
    ATTR_SERVICE,
    ATTR_SUBMIT_PERIOD_ACTIVE,
    ATTR_SUBMIT_PERIOD_END,
    ATTR_SUBMIT_PERIOD_START,
    ATTR_TAX,
    ATTR_TAX_AMOUNT,
    ATTR_TEXT,
    ATTR_VOLUME,
    CURRENCY_RUB,
    OPTION_SHOW_CHARGED,
    OPTION_SHOW_CHARGE_HISTORY,
    OPTION_SHOW_COUNTERS,
    OPTION_SHOW_DUE_SEGMENTS,
    OPTION_SHOW_LAST_PAYMENT,
    OPTION_SHOW_PAID,
    OPTION_SHOW_RECEIPTS,
    counters_submit_window,
    option_enabled,
    submit_window_active,
)
from .coordinator import DmvlDataUpdateCoordinator
from .entity import DmvlEntity

# Read-only state from the shared coordinator; no outbound action.
PARALLEL_UPDATES = 0


def _reading_order_key(reading: CounterReading) -> tuple[str, str]:
    """Sort key for reading recency: by period end, then period start.

    ISO dates compare lexicographically. A missing period end yields the
    smallest key, so such a reading is picked only when it is the sole one
    (spec 0014 R2). ``period_start`` is a secondary tiebreaker.
    """
    return (reading.period_end or "", reading.period_start or "")


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


class DmvlCounterSensor(DmvlEntity, SensorEntity):
    """A meter reading (spec 0013 R2).

    One entity per ``Session.counters`` entry, keyed by the meter serial. The
    meter set is fixed at setup; a meter added later appears after a reload.
    """

    _entity_id_domain = Platform.SENSOR
    _attr_translation_key: str | None = None

    def __init__(
        self,
        coordinator: DmvlDataUpdateCoordinator,
        entry: ConfigEntry,
        counter: Counter,
    ) -> None:
        slug = slugify(counter.serial) or "meter"
        super().__init__(coordinator, entry, f"counter_{slug}")
        self._attr_unique_id = f"{entry.entry_id}_counter_{counter.serial or slug}"
        self._attr_translation_key = None
        self._serial = counter.serial
        self._attr_name = counter.name or counter.service or counter.serial

    def _counter(self) -> Counter | None:
        """The latest snapshot's meter with this serial, if still present."""
        for counter in self.coordinator.data.counters:
            if counter.serial == self._serial:
                return counter
        return None

    def _selected_reading(self, counter: Counter) -> tuple[CounterReading | None, bool]:
        """The actual reading, else the latest one (spec 0014 R1/R2).

        Returns the reading and whether it is the actual one. The latest
        reading is chosen by ``period_end`` (missing dates sort last); an empty
        history yields ``(None, False)``.
        """
        actual = counter.current_reading
        if actual is not None:
            return actual, True
        latest: CounterReading | None = None
        for reading in counter.readings:
            if latest is None or _reading_order_key(reading) > _reading_order_key(latest):
                latest = reading
        return latest, False

    @property
    def available(self) -> bool:
        return super().available and self._counter() is not None

    @property
    def native_value(self) -> float | None:
        counter = self._counter()
        if counter is None:
            return None
        reading, _ = self._selected_reading(counter)
        return float(reading.reading) if reading is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        counter = self._counter()
        if counter is None:
            return None
        settings = self.coordinator.data.account.settings
        attributes: dict[str, Any] = {}

        def put(key: str, value: Any) -> None:
            if value is not None and value != "":
                attributes[key] = value

        put(ATTR_SERIAL, self._serial)
        put(ATTR_SERVICE, counter.service)
        put(ATTR_CHECKED, counter.checked)
        selected, is_actual = self._selected_reading(counter)
        if selected is not None:
            put(ATTR_VOLUME, float(selected.volume))
            put(ATTR_KIND, selected.kind)
            put(ATTR_PERIOD_START, selected.period_start)
            put(ATTR_PERIOD_END, selected.period_end)
            attributes[ATTR_IS_ACTUAL] = is_actual
        put(
            ATTR_READINGS,
            [
                {
                    ATTR_PERIOD_START: reading.period_start,
                    ATTR_PERIOD_END: reading.period_end,
                    ATTR_READING: float(reading.reading),
                    ATTR_VOLUME: float(reading.volume),
                    ATTR_KIND: reading.kind,
                    ATTR_IS_ACTUAL: reading.is_actual,
                }
                for reading in counter.readings
            ],
        )
        start, end = counters_submit_window(settings)
        put(ATTR_SUBMIT_PERIOD_START, start)
        put(ATTR_SUBMIT_PERIOD_END, end)
        active = submit_window_active(settings, dt_util.now().day)
        if active is not None:
            attributes[ATTR_SUBMIT_PERIOD_ACTIVE] = active
        return attributes or None


class DmvlReceiptsSensor(DmvlEntity, SensorEntity):
    """Number of receipt links with the links as attributes (spec 0013 R3)."""

    _entity_id_domain = Platform.SENSOR

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "receipts")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.receipts)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        receipts = self.coordinator.data.receipts
        if not receipts:
            return None
        return {
            ATTR_RECEIPTS: [
                {ATTR_KIND: receipt.kind, ATTR_NAME: receipt.name, ATTR_LINK: receipt.link}
                for receipt in receipts
            ]
        }


class DmvlChargeHistorySensor(DmvlEntity, SensorEntity):
    """Number of charge periods with the period rows as attributes (0013 R4)."""

    _entity_id_domain = Platform.SENSOR

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "charge_history")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.charges)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        charges = self.coordinator.data.charges
        if not charges:
            return None
        return {
            ATTR_PERIODS: [
                {
                    ATTR_DATE: charge.date,
                    ATTR_CHARGED: float(charge.charged),
                    ATTR_CHARGED_ADJUSTED: float(charge.charged_adjusted),
                    ATTR_BENEFIT: float(charge.benefit),
                    ATTR_DIFFERENCE: float(charge.difference),
                    ATTR_PAID: float(charge.paid),
                    ATTR_DEBT_OPENING: float(charge.debt_opening),
                    ATTR_DEBT_CLOSING: float(charge.debt_closing),
                    ATTR_IS_PAID: charge.is_paid,
                }
                for charge in charges
            ]
        }


class DmvlDueSegmentsSensor(DmvlEntity, SensorEntity):
    """Amount due by payment channel (spec 0013 R5).

    State is the number of payment segments; the segments themselves and the
    payment text are attributes. Unavailable when the optional ``getpayments``
    request failed while the account snapshot stayed valid (R6).
    """

    _entity_id_domain = Platform.SENSOR

    def __init__(self, coordinator: DmvlDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "due_segments")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.payment_options is not None

    @property
    def native_value(self) -> int | None:
        options = self.coordinator.payment_options
        return options.count if options is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        options = self.coordinator.payment_options
        if options is None:
            return None

        def put(key: str, value: Any) -> None:
            if value is not None and value != "":
                attributes[key] = value

        attributes: dict[str, Any] = {}
        put(ATTR_TEXT, options.text)
        attributes[ATTR_HIDE_SUM_WITH_TAX] = options.hide_sum_with_tax
        put(
            ATTR_SEGMENTS,
            [
                {
                    ATTR_PAYMENT_ID: segment.payment_id,
                    ATTR_PROVIDER: segment.provider,
                    ATTR_BUTTON: segment.button,
                    ATTR_AMOUNT: float(segment.amount),
                    ATTR_TAX: float(segment.tax),
                    ATTR_TAX_AMOUNT: float(segment.tax_amount),
                    ATTR_INPUT: float(segment.input),
                }
                for segment in options.segments
            ],
        )
        return attributes or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the sensors selected by the options (spec 0002 R4, 0006 R3, 0013)."""
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
    if option_enabled(options, OPTION_SHOW_COUNTERS):
        entities.extend(
            DmvlCounterSensor(coordinator, entry, counter)
            for counter in coordinator.data.counters
        )
    if option_enabled(options, OPTION_SHOW_RECEIPTS):
        entities.append(DmvlReceiptsSensor(coordinator, entry))
    if option_enabled(options, OPTION_SHOW_CHARGE_HISTORY):
        entities.append(DmvlChargeHistorySensor(coordinator, entry))
    if option_enabled(options, OPTION_SHOW_DUE_SEGMENTS):
        entities.append(DmvlDueSegmentsSensor(coordinator, entry))
    async_add_entities(entities)
