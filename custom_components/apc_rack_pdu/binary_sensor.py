"""Binary sensors for APC Metered Rack PDU."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ApcRackPduCoordinator

BINARY_SENSORS = (
    BinarySensorEntityDescription(
        key="overload",
        translation_key="overload",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="near_overload",
        translation_key="near_overload",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: ApcRackPduCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ApcRackPduBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class ApcRackPduBinarySensor(
    CoordinatorEntity[ApcRackPduCoordinator], BinarySensorEntity
):
    """Binary sensor for load-state thresholds."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ApcRackPduCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = (coordinator.data.serial if coordinator.data else None) or entry.unique_id
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial or entry.entry_id)},
            name=entry.title,
            manufacturer="APC / Schneider Electric",
            model=coordinator.data.model if coordinator.data else None,
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the condition is active."""
        data = self.coordinator.data
        if not data or not data.load_state:
            return None
        if self.entity_description.key == "overload":
            return data.load_state == "overload"
        if self.entity_description.key == "near_overload":
            return data.load_state in {"near_overload", "overload"}
        return None
