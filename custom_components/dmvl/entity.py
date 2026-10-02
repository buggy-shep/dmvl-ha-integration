"""Shared entity plumbing for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_LOGIN, DOMAIN, MANUFACTURER, MODEL
from .coordinator import DmvlDataUpdateCoordinator


class DmvlEntity(CoordinatorEntity[DmvlDataUpdateCoordinator]):
    """Base entity: per-entry device identity and coordinator updates.

    The device is identified by the config entry id (never the account login),
    so no account data reaches the device registry identifiers; the device
    *name* combines the management organization and the account code
    (spec 0011 R4).

    The entity id is suggested explicitly as `dmvl_<login>_<suffix>`, so it is
    stable and account-specific and does not drift with the user-changeable
    device name or area (spec 0009).
    """

    _attr_has_entity_name = True
    _entity_id_domain: Platform

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
            name=entry.runtime_data.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        slug = slugify(entry.data.get(CONF_LOGIN, ""))
        if slug in ("", "unknown"):
            slug = entry.entry_id[:8]
        self.entity_id = f"{self._entity_id_domain}.{DOMAIN}_{slug}_{suffix}"
