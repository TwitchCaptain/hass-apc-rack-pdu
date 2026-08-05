"""Button entities for APC Metered Rack PDU actions."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import ApcRackPduCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ApcButtonEntityDescription(ButtonEntityDescription):
    """Button description with press handler."""

    press_fn: Callable[[ApcRackPduCoordinator], Awaitable[None]]
    needs_ssh: bool = False


async def _reset_energy(coordinator: ApcRackPduCoordinator) -> None:
    await coordinator.client.reset_energy()
    await coordinator.async_request_refresh()


async def _reset_peak(coordinator: ApcRackPduCoordinator) -> None:
    await coordinator.client.reset_peak_power()
    await coordinator.async_request_refresh()


async def _blink_lcd(coordinator: ApcRackPduCoordinator) -> None:
    """Blink the PDU LCD via SSH (same trick as the Indigo plugin)."""
    import asyncio

    host = coordinator.entry.data["host"]
    user = coordinator.entry.data.get(CONF_USERNAME, "apc")
    password = coordinator.entry.data.get(CONF_PASSWORD, "apc")

    script = f"""
set timeout 20
spawn ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no {user}@{host}
expect {{
  -re "(?i)password:" {{ send "{password}\\r" }}
  timeout {{ exit 1 }}
  eof {{ exit 1 }}
}}
expect {{
  "apc>" {{ send "lcdblink 1\\r" }}
  timeout {{ exit 2 }}
}}
expect "apc>"
send "quit\\r"
expect eof
"""
    proc = await asyncio.create_subprocess_exec(
        "expect",
        "-c",
        script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"LCD blink failed (rc={proc.returncode}): {stderr.decode(errors='replace')}"
        )


BUTTONS: tuple[ApcButtonEntityDescription, ...] = (
    ApcButtonEntityDescription(
        key="reset_energy",
        translation_key="reset_energy",
        icon="mdi:reload",
        entity_category=EntityCategory.CONFIG,
        press_fn=_reset_energy,
    ),
    ApcButtonEntityDescription(
        key="reset_peak_power",
        translation_key="reset_peak_power",
        icon="mdi:chart-line",
        entity_category=EntityCategory.CONFIG,
        press_fn=_reset_peak,
    ),
    ApcButtonEntityDescription(
        key="identify",
        translation_key="identify",
        icon="mdi:cellphone-wireless",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=_blink_lcd,
        needs_ssh=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons."""
    coordinator: ApcRackPduCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for description in BUTTONS:
        if description.needs_ssh and not entry.data.get(CONF_USERNAME):
            # Still allow default apc/apc if password provided or always try identify
            pass
        entities.append(ApcRackPduButton(coordinator, entry, description))
    async_add_entities(entities)


class ApcRackPduButton(CoordinatorEntity[ApcRackPduCoordinator], ButtonEntity):
    """Button that triggers a PDU action."""

    entity_description: ApcButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ApcRackPduCoordinator,
        entry: ConfigEntry,
        description: ApcButtonEntityDescription,
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

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)
