"""Unit tests for APC PDU parsing helpers and coordinator refresh."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from custom_components.apc_rack_pdu.const import (
    OID_ENERGY,
    OID_HUMIDITY,
    OID_LOAD_STATE,
    OID_MAX_CURRENT,
    OID_NAME,
    OID_NUM_OUTLETS,
    OID_PHASE_CURRENT,
    OID_PHASE_LOAD_STATE,
    OID_PHASE_VOLTAGE,
    OID_POWER,
    OID_PROBE_COMM,
    OID_PROBE_NAME,
    OID_SERIAL,
    OID_TEMP_C,
    OID_TEMP_F,
)
from custom_components.apc_rack_pdu.coordinator import (
    ApcRackPduCoordinator,
    _as_int,
    _as_str,
    _hundredths_kw_to_w,
    _hundredths_to_ratio,
    _tenths_to_float,
)

from .conftest import ENTRY_DATA, SERIAL


def test_as_int_handles_missing_and_junk():
    assert _as_int(None) is None
    assert _as_int("noSuchInstance") is None
    assert _as_int("") is None
    assert _as_int("42") == 42
    assert _as_int(7) == 7


def test_as_str_strips_quotes():
    assert _as_str(None) is None
    assert _as_str(' "AP8858" ') == "AP8858"
    assert _as_str("noSuchObject") is None


def test_scale_helpers():
    assert _hundredths_kw_to_w(45) == 450.0
    assert _hundredths_kw_to_w(-1) is None
    assert _tenths_to_float(123) == 12.3
    assert _hundredths_to_ratio(95) == 0.95


async def test_coordinator_parses_snmp_values(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    client = MagicMock()
    client.host = ENTRY_DATA["host"]
    client.get_many = AsyncMock(
        side_effect=[
            {
                OID_NAME: "Rack PDU",
                OID_SERIAL: SERIAL,
                OID_NUM_OUTLETS: 24,
                OID_MAX_CURRENT: 20,
                OID_LOAD_STATE: 2,
                OID_POWER: 45,
                OID_ENERGY: 123,
                OID_PHASE_LOAD_STATE: 2,
                OID_PHASE_CURRENT: 35,
                OID_PHASE_VOLTAGE: 120,
            },
            {
                OID_PROBE_NAME: "Probe 1",
                OID_PROBE_COMM: 2,
                OID_TEMP_F: 780,
                OID_TEMP_C: 256,
                OID_HUMIDITY: 42,
            },
        ]
    )

    coordinator = ApcRackPduCoordinator(hass, mock_config_entry, client)
    data = await coordinator._async_update_data()

    assert data.serial == SERIAL
    assert data.power_w == 450.0
    assert data.energy_kwh == 12.3
    assert data.current_a == 3.5
    assert data.voltage_v == 120.0
    assert data.load_state == "normal"
    assert data.load_percent == 17.5
    assert data.has_env_probe is True
    assert data.temperature_f == 78.0
    assert data.humidity == 42.0
