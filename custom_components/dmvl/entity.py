"""Shared entity plumbing for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import DmvlDataUpdateCoordinator


class DmvlEntity(CoordinatorEntity[DmvlDataUpdateCoordinator]):
    """Base entity: per-entry device identity and coordinator updates.

    The device is identified by the config entry id (never the account login),
    so no account data reaches the device registry.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DmvlDataUpdateCoordinator,
        entry: ConfigEntry,
        suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_translation_key = suffix
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
