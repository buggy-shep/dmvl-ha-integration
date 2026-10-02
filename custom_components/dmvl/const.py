"""Constants for the Domovladelets integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dmvl"

MANUFACTURER: Final = "Domovladelets"
MODEL: Final = "Account"
DEVICE_NAME: Final = "Domovladelets"

CONF_LOGIN: Final = "login"
CONF_PASSWORD: Final = "password"
CONF_VERIFY: Final = "verify"

DEFAULT_VERIFY: Final = False
DEFAULT_SCAN_INTERVAL: Final = timedelta(hours=1)

CURRENCY_RUB: Final = "RUB"

ATTR_AMOUNT: Final = "amount"
