"""Sensor platform for APC Metered Rack PDU."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ApcRackPduCoordinator, PduData


@dataclass(frozen=True, kw_only=True)
class ApcSensorEntityDescription(SensorEntityDescription):
    """Describes an APC PDU sensor."""

    value_fn: Callable[[PduData], Any]
    env_only: bool = False


SENSORS: tuple[ApcSensorEntityDescription, ...] = (
    ApcSensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.power_w,
    ),
    ApcSensorEntityDescription(
        key="peak_power",
        translation_key="peak_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.peak_power_w,
    ),
    ApcSensorEntityDescription(
        key="energy",
        translation_key="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda d: d.energy_kwh,
    ),
    ApcSensorEntityDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=lambda d: d.current_a,
    ),
    ApcSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=0,
        value_fn=lambda d: d.voltage_v,
    ),
    ApcSensorEntityDescription(
        key="apparent_power",
        translation_key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="VA",
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.apparent_power_va,
    ),
    ApcSensorEntityDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.power_factor or d.phase_power_factor,
    ),
    ApcSensorEntityDescription(
        key="load_percent",
        translation_key="load_percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        icon="mdi:gauge",
        value_fn=lambda d: d.load_percent,
    ),
    ApcSensorEntityDescription(
        key="load_state",
        translation_key="load_state",
        device_class=SensorDeviceClass.ENUM,
        options=["low", "normal", "near_overload", "overload"],
        icon="mdi:lightning-bolt",
        value_fn=lambda d: d.load_state,
    ),
    ApcSensorEntityDescription(
        key="peak_current",
        translation_key="peak_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.peak_current_a,
    ),
    ApcSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        suggested_display_precision=1,
        env_only=True,
        value_fn=lambda d: d.temperature_f,
    ),
    ApcSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        env_only=True,
        value_fn=lambda d: d.humidity,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up APC PDU sensors."""
    coordinator: ApcRackPduCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ApcRackPduSensor] = []
    for description in SENSORS:
        if description.env_only and not (
            coordinator.data and coordinator.data.has_env_probe
        ):
            continue
        entities.append(ApcRackPduSensor(coordinator, entry, description))
    async_add_entities(entities)


class ApcRackPduSensor(CoordinatorEntity[ApcRackPduCoordinator], SensorEntity):
    """Sensor for one PDU metric."""

    entity_description: ApcSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ApcRackPduCoordinator,
        entry: ConfigEntry,
        description: ApcSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = (coordinator.data.serial if coordinator.data else None) or entry.unique_id
        self._attr_unique_id = f"{serial}_{description.key}"
        model = coordinator.data.model if coordinator.data else None
        name = coordinator.data.name if coordinator.data else entry.title
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial or entry.entry_id)},
            name=entry.title or name or "APC Rack PDU",
            manufacturer="APC / Schneider Electric",
            model=model,
            sw_version=coordinator.data.firmware if coordinator.data else None,
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
