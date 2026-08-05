"""Shared fixtures for apc_rack_pdu component tests."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apc_rack_pdu.const import (
    CONF_COMMUNITY,
    CONF_HAS_ENV_PROBE,
    CONF_WRITE_COMMUNITY,
    DOMAIN,
)
from custom_components.apc_rack_pdu.coordinator import PduData

SERIAL = "QA1234567890"


# pytest-homeassistant-custom-component 0.13.x defines `enable_event_loop_debug`
# as a plain `@pytest.fixture(autouse=True)` async generator, which pytest 9
# rejects. Override it locally until the upstream plugin handles pytest 9.
@pytest_asyncio.fixture(autouse=True)
async def enable_event_loop_debug() -> None:
    """Enable event loop debug mode."""
    asyncio.get_running_loop().set_debug(True)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let the HA test harness discover custom_components/apc_rack_pdu."""
    return


# Fields accepted by the user config-flow schema (has_env_probe is derived).
USER_INPUT: dict[str, Any] = {
    CONF_HOST: "pdu.local",
    CONF_NAME: "Rack PDU",
    CONF_COMMUNITY: "public",
    CONF_WRITE_COMMUNITY: "private",
    CONF_PORT: 161,
    CONF_SCAN_INTERVAL: 30,
}

ENTRY_DATA: dict[str, Any] = {
    **USER_INPUT,
    CONF_HAS_ENV_PROBE: True,
}


def make_pdu_data(**kwargs: Any) -> PduData:
    """Build PduData with sensible defaults for tests."""
    defaults: dict[str, Any] = {
        "name": "Rack PDU",
        "location": "Closet",
        "model": "AP8858",
        "serial": SERIAL,
        "firmware": "v1.0",
        "num_outlets": 24,
        "max_current": 20.0,
        "load_state": "normal",
        "load_state_raw": 2,
        "power_w": 450.0,
        "peak_power_w": 800.0,
        "energy_kwh": 12.3,
        "power_factor": 0.95,
        "phase_load_state": "normal",
        "current_a": 3.5,
        "voltage_v": 120.0,
        "phase_power_w": 450.0,
        "apparent_power_va": 480.0,
        "phase_power_factor": 0.95,
        "peak_current_a": 6.0,
        "load_percent": 17.5,
        "has_env_probe": True,
        "probe_name": "Probe 1",
        "temperature_f": 78.0,
        "temperature_c": 25.6,
        "humidity": 42.0,
    }
    defaults.update(kwargs)
    return PduData(**defaults)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Config entry with typical user input."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Rack PDU",
        data=ENTRY_DATA,
        unique_id=SERIAL,
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock SNMP client used during setup."""
    client = MagicMock()
    client.host = ENTRY_DATA[CONF_HOST]
    client.fetch_identity = AsyncMock(
        return_value={
            "name": "Rack PDU",
            "model": "AP8858",
            "serial": SERIAL,
            "firmware": "v1.0",
            "location": "Closet",
            "has_env_probe": True,
        }
    )
    client.get_many = AsyncMock(return_value={})
    client.reset_energy = AsyncMock()
    client.reset_peak_power = AsyncMock()
    client.set_integer = AsyncMock()
    return client


@pytest.fixture
async def setup_entry(hass, mock_config_entry, mock_client) -> MockConfigEntry:
    """Set the integration up fully against the mocked client/coordinator."""
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.apc_rack_pdu.ApcRackPduClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.apc_rack_pdu.coordinator.ApcRackPduCoordinator._async_update_data",
            AsyncMock(return_value=make_pdu_data()),
        ),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry
