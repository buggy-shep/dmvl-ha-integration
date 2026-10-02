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

OPTION_DEFAULTS: Final[dict[str, Any]] = {
    OPTION_SHOW_CHARGED: True,
    OPTION_SHOW_PAID: True,
    OPTION_SHOW_LAST_PAYMENT: True,
    OPTION_SCAN_INTERVAL_HOURS: 6,
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


def option_enabled(options: Mapping[str, Any], key: str) -> bool:
    """Whether an optional entity is enabled (spec 0006 R5)."""
    value = options.get(key, OPTION_DEFAULTS[key])
    return bool(value)


def scan_interval_hours(options: Mapping[str, Any]) -> int:
    """Configured polling interval, clamped to the allowed bounds (spec 0007)."""
    try:
        value = int(options.get(OPTION_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS))
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL_HOURS
    return max(MIN_SCAN_INTERVAL_HOURS, min(MAX_SCAN_INTERVAL_HOURS, value))
