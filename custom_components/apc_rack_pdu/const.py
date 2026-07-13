"""Constants for the APC Metered Rack PDU integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "apc_rack_pdu"
DEFAULT_NAME: Final = "Rack PDU"
DEFAULT_COMMUNITY: Final = "public"
DEFAULT_WRITE_COMMUNITY: Final = "private"
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
DEFAULT_PORT: Final = 161

# PowerNet-MIB rPDU2 identity (index .1)
OID_NAME = "1.3.6.1.4.1.318.1.1.26.2.1.3.1"
OID_LOCATION = "1.3.6.1.4.1.318.1.1.26.2.1.4.1"
OID_FIRMWARE = "1.3.6.1.4.1.318.1.1.26.2.1.6.1"
OID_MODEL = "1.3.6.1.4.1.318.1.1.26.2.1.8.1"
OID_SERIAL = "1.3.6.1.4.1.318.1.1.26.2.1.9.1"

# Device properties
OID_NUM_OUTLETS = "1.3.6.1.4.1.318.1.1.26.4.2.1.4.1"
OID_NUM_PHASES = "1.3.6.1.4.1.318.1.1.26.4.2.1.7.1"
OID_MAX_CURRENT = "1.3.6.1.4.1.318.1.1.26.4.2.1.9.1"

# Device status
OID_LOAD_STATE = "1.3.6.1.4.1.318.1.1.26.4.3.1.4.1"
OID_POWER = "1.3.6.1.4.1.318.1.1.26.4.3.1.5.1"  # hundredths of kW
OID_PEAK_POWER = "1.3.6.1.4.1.318.1.1.26.4.3.1.6.1"  # hundredths of kW
OID_ENERGY = "1.3.6.1.4.1.318.1.1.26.4.3.1.9.1"  # tenths of kWh
OID_POWER_FACTOR = "1.3.6.1.4.1.318.1.1.26.4.3.1.17.1"  # hundredths

# Phase 1 status
OID_PHASE_LOAD_STATE = "1.3.6.1.4.1.318.1.1.26.6.3.1.4.1"
OID_PHASE_CURRENT = "1.3.6.1.4.1.318.1.1.26.6.3.1.5.1"  # tenths of A
OID_PHASE_VOLTAGE = "1.3.6.1.4.1.318.1.1.26.6.3.1.6.1"  # V
OID_PHASE_POWER = "1.3.6.1.4.1.318.1.1.26.6.3.1.7.1"  # hundredths of kW
OID_PHASE_APPARENT = "1.3.6.1.4.1.318.1.1.26.6.3.1.8.1"  # hundredths of kVA
OID_PHASE_PF = "1.3.6.1.4.1.318.1.1.26.6.3.1.9.1"  # hundredths
OID_PHASE_PEAK_CURRENT = "1.3.6.1.4.1.318.1.1.26.6.3.1.10.1"  # tenths of A

# Env probe (optional AP9335TH / similar)
OID_PROBE_NAME = "1.3.6.1.4.1.318.1.1.26.10.2.2.1.3.1"
OID_PROBE_COMM = "1.3.6.1.4.1.318.1.1.26.10.2.2.1.6.1"
OID_TEMP_F = "1.3.6.1.4.1.318.1.1.26.10.2.2.1.7.1"  # tenths °F
OID_TEMP_C = "1.3.6.1.4.1.318.1.1.26.10.2.2.1.8.1"  # tenths °C
OID_HUMIDITY = "1.3.6.1.4.1.318.1.1.26.10.2.2.1.10.1"  # % RH

# SNMP write controls (set to 2 = reset)
OID_RESET_PEAK_POWER = "1.3.6.1.4.1.318.1.1.26.4.1.1.10.1"
OID_RESET_ENERGY = "1.3.6.1.4.1.318.1.1.26.4.1.1.11.1"
SNMP_RESET = 2

LOAD_STATE_MAP: Final[dict[int, str]] = {
    1: "low",
    2: "normal",
    3: "near_overload",
    4: "overload",
}

CONF_COMMUNITY = "community"
CONF_WRITE_COMMUNITY = "write_community"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_HAS_ENV_PROBE = "has_env_probe"

ATTR_SERIAL = "serial_number"
ATTR_MODEL = "model"
ATTR_FIRMWARE = "firmware"
ATTR_LOCATION = "location"
ATTR_NUM_OUTLETS = "num_outlets"
ATTR_MAX_CURRENT = "max_current_amps"
