"""Binary sensors for the Domovladelets integration (spec 0002)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DmvlRuntimeData
from .entity import DmvlEntity

# Read-only state from the shared coordinator; no outbound action.
PARALLEL_UPDATES = 0


class DmvlUnpaidDocumentsBinarySensor(DmvlEntity, BinarySensorEntity):
    """On when any document is unpaid (spec 0002 R4)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "unpaid_documents")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.has_unpaid_documents


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the binary sensors of a config entry."""
    runtime: DmvlRuntimeData = entry.runtime_data
    async_add_entities([DmvlUnpaidDocumentsBinarySensor(runtime.coordinator, entry)])
