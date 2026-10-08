"""Constants for the Domovladelets integration."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, Final

DOMAIN: Final = "dmvl"

MANUFACTURER: Final = "Domovladelets"
MODEL: Final = "Account"
DEVICE_NAME: Final = "Domovladelets"

CONF_LOGIN: Final = "login"
CONF_PASSWORD: Final = "password"
CONF_VERIFY: Final = "verify"

# Options flow (spec 0006): optional entities, all enabled by default.
OPTION_SHOW_CHARGED: Final = "show_charged"
OPTION_SHOW_PAID: Final = "show_paid"
OPTION_SHOW_LAST_PAYMENT: Final = "show_last_payment"
# Options flow (spec 0007): polling interval in hours.
OPTION_SCAN_INTERVAL_HOURS: Final = "scan_interval_hours"
# Options flow (spec 0013): read-only entity expansion, disabled by default so
# the minimal default set is preserved (plan D3).
OPTION_SHOW_COUNTERS: Final = "show_counters"
OPTION_SHOW_RECEIPTS: Final = "show_receipts"
OPTION_SHOW_CHARGE_HISTORY: Final = "show_charge_history"
OPTION_SHOW_DUE_SEGMENTS: Final = "show_due_segments"

OPTION_DEFAULTS: Final[dict[str, Any]] = {
    OPTION_SHOW_CHARGED: True,
    OPTION_SHOW_PAID: True,
    OPTION_SHOW_LAST_PAYMENT: True,
    OPTION_SCAN_INTERVAL_HOURS: 6,
    OPTION_SHOW_COUNTERS: False,
    OPTION_SHOW_RECEIPTS: False,
    OPTION_SHOW_CHARGE_HISTORY: False,
    OPTION_SHOW_DUE_SEGMENTS: False,
}

DEFAULT_VERIFY: Final = False
DEFAULT_SCAN_INTERVAL_HOURS: Final = 6
MIN_SCAN_INTERVAL_HOURS: Final = 1
MAX_SCAN_INTERVAL_HOURS: Final = 24
DEFAULT_SCAN_INTERVAL: Final = timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS)

SERVICE_REFRESH: Final = "refresh"

CURRENCY_RUB: Final = "RUB"

ATTR_AMOUNT: Final = "amount"
ATTR_DATE: Final = "date"
ATTR_PERIOD: Final = "period"
ATTR_PAYMENT_PURPOSE: Final = "payment_purpose"
ATTR_LAST_PAYMENT_DATE: Final = "last_payment_date"
ATTR_PAYMENTS: Final = "payments"
ATTR_HAS_DEBT: Final = "has_debt"
ATTR_UNPAID_PERIODS: Final = "unpaid_periods"

# Meter sensors (spec 0013 R2).
ATTR_SERIAL: Final = "serial"
ATTR_SERVICE: Final = "service"
ATTR_VOLUME: Final = "volume"
ATTR_KIND: Final = "kind"
ATTR_PERIOD_START: Final = "period_start"
ATTR_PERIOD_END: Final = "period_end"
ATTR_CHECKED: Final = "checked"
ATTR_READINGS: Final = "readings"
ATTR_READING: Final = "reading"
ATTR_IS_ACTUAL: Final = "is_actual"
ATTR_SUBMIT_PERIOD_START: Final = "submit_period_start"
ATTR_SUBMIT_PERIOD_END: Final = "submit_period_end"
ATTR_SUBMIT_PERIOD_ACTIVE: Final = "submit_period_active"

# Receipts, history and due segments (spec 0013 R3/R4/R5).
ATTR_NAME: Final = "name"
ATTR_LINK: Final = "link"
ATTR_RECEIPTS: Final = "receipts"
ATTR_PERIODS: Final = "periods"
ATTR_CHARGED: Final = "charged"
ATTR_CHARGED_ADJUSTED: Final = "charged_adjusted"
ATTR_BENEFIT: Final = "benefit"
ATTR_DIFFERENCE: Final = "difference"
ATTR_PAID: Final = "paid"
ATTR_DEBT_OPENING: Final = "debt_opening"
ATTR_DEBT_CLOSING: Final = "debt_closing"
ATTR_IS_PAID: Final = "is_paid"
ATTR_SEGMENTS: Final = "segments"
ATTR_TEXT: Final = "text"
ATTR_HIDE_SUM_WITH_TAX: Final = "hide_sum_with_tax"
ATTR_PAYMENT_ID: Final = "payment_id"
ATTR_PROVIDER: Final = "provider"
ATTR_BUTTON: Final = "button"
ATTR_TAX: Final = "tax"
ATTR_TAX_AMOUNT: Final = "tax_amount"
ATTR_INPUT: Final = "input"

# Account settings that bound the monthly meter-reading submission window.
SETTING_FIRST_DAY_COUNTERS: Final = "first_day_counters_values"
SETTING_LAST_DAY_COUNTERS: Final = "last_day_counters_values"


def option_enabled(options: Mapping[str, Any], key: str) -> bool:
    """Whether an optional entity is enabled (spec 0006 R5)."""
    value = options.get(key, OPTION_DEFAULTS[key])
    return bool(value)


def _setting_day(settings: Mapping[str, Any], key: str) -> int | None:
    """Parse a day-of-month setting into 1..31, or ``None`` when unusable."""
    raw = settings.get(key)
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 31 else None


def counters_submit_window(settings: Mapping[str, Any]) -> tuple[int | None, int | None]:
    """The meter submission window (start, end) from the account settings.

    Either bound is ``None`` when the service did not provide a usable day
    (spec 0013 R2).
    """
    return _setting_day(settings, SETTING_FIRST_DAY_COUNTERS), _setting_day(
        settings, SETTING_LAST_DAY_COUNTERS
    )


def submit_window_active(settings: Mapping[str, Any], day: int) -> bool | None:
    """Whether ``day`` falls in the submission window, or ``None`` if unknown.

    Supports a window that wraps the month end (for example 25..5).
    """
    start, end = counters_submit_window(settings)
    if start is None or end is None:
        return None
    if start <= end:
        return start <= day <= end
    return day >= start or day <= end


def scan_interval_hours(options: Mapping[str, Any]) -> int:
    """Configured polling interval, clamped to the allowed bounds (spec 0007)."""
    try:
        value = int(options.get(OPTION_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS))
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL_HOURS
    return max(MIN_SCAN_INTERVAL_HOURS, min(MAX_SCAN_INTERVAL_HOURS, value))
