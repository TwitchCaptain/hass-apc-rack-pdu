"""SNMP helpers and data coordinator for APC Metered Rack PDU."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.snmp import async_get_snmp_engine
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
    set_cmd,
)

from .const import (
    ATTR_FIRMWARE,
    ATTR_LOCATION,
    ATTR_MAX_CURRENT,
    ATTR_MODEL,
    ATTR_NUM_OUTLETS,
    ATTR_SERIAL,
    CONF_HAS_ENV_PROBE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOAD_STATE_MAP,
    OID_ENERGY,
    OID_FIRMWARE,
    OID_HUMIDITY,
    OID_LOAD_STATE,
    OID_LOCATION,
    OID_MAX_CURRENT,
    OID_MODEL,
    OID_NAME,
    OID_NUM_OUTLETS,
    OID_PEAK_POWER,
    OID_PHASE_APPARENT,
    OID_PHASE_CURRENT,
    OID_PHASE_LOAD_STATE,
    OID_PHASE_PEAK_CURRENT,
    OID_PHASE_PF,
    OID_PHASE_POWER,
    OID_PHASE_VOLTAGE,
    OID_POWER,
    OID_POWER_FACTOR,
    OID_PROBE_COMM,
    OID_PROBE_NAME,
    OID_RESET_ENERGY,
    OID_RESET_PEAK_POWER,
    OID_SERIAL,
    OID_TEMP_C,
    OID_TEMP_F,
    SNMP_RESET,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PduData:
    """Parsed PDU telemetry."""

    name: str | None = None
    location: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    num_outlets: int | None = None
    max_current: float | None = None
    load_state: str | None = None
    load_state_raw: int | None = None
    power_w: float | None = None
    peak_power_w: float | None = None
    energy_kwh: float | None = None
    power_factor: float | None = None
    phase_load_state: str | None = None
    current_a: float | None = None
    voltage_v: float | None = None
    phase_power_w: float | None = None
    apparent_power_va: float | None = None
    phase_power_factor: float | None = None
    peak_current_a: float | None = None
    load_percent: float | None = None
    has_env_probe: bool = False
    probe_name: str | None = None
    temperature_f: float | None = None
    temperature_c: float | None = None
    humidity: float | None = None


def _as_int(value: Any) -> int | None:
    """Convert SNMP value to int."""
    if value is None:
        return None
    text = str(value)
    if text in {"", "None", "noSuchObject", "noSuchInstance", "endOfMibView"}:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    """Convert SNMP value to stripped string."""
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if text in {"", "None", "noSuchObject", "noSuchInstance", "endOfMibView"}:
        return None
    return text


def _hundredths_kw_to_w(raw: int | None) -> float | None:
    """Convert hundredths of kW to watts."""
    if raw is None or raw < 0:
        return None
    return round(raw * 10.0, 1)


def _tenths_to_float(raw: int | None) -> float | None:
    """Convert tenths to float."""
    if raw is None or raw < 0:
        return None
    return round(raw / 10.0, 1)


def _hundredths_to_ratio(raw: int | None) -> float | None:
    """Convert hundredths to 0-1 ratio."""
    if raw is None or raw < 0:
        return None
    return round(raw / 100.0, 2)


class ApcRackPduClient:
    """Async SNMP client for APC rPDU2 devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        community: str,
        write_community: str,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.hass = hass
        self.host = host
        self.community = community
        self.write_community = write_community
        self.port = port
        self._engine: SnmpEngine | None = None

    async def _engine_ready(self) -> SnmpEngine:
        if self._engine is None:
            self._engine = await async_get_snmp_engine(self.hass)
        return self._engine

    async def _target(self) -> UdpTransportTarget:
        return await UdpTransportTarget.create(
            (self.host, self.port), timeout=2.0, retries=1
        )

    async def get_many(self, oids: list[str]) -> dict[str, Any]:
        """GET multiple OIDs and return a map keyed by requested OID."""
        engine = await self._engine_ready()
        target = await self._target()
        err_indication, err_status, _err_index, var_binds = await get_cmd(
            engine,
            CommunityData(self.community, mpModel=0),
            target,
            ContextData(),
            *[ObjectType(ObjectIdentity(oid)) for oid in oids],
        )
        if err_indication:
            raise UpdateFailed(f"SNMP error contacting {self.host}: {err_indication}")
        if err_status:
            # Partial failures are common for optional probe OIDs; continue with what we got.
            _LOGGER.debug(
                "SNMP status %s from %s (continuing with partial results)",
                err_status.prettyPrint(),
                self.host,
            )

        results: dict[str, Any] = {}
        for requested, var_bind in zip(oids, var_binds, strict=False):
            _name, value = var_bind
            results[requested] = value
        return results

    async def set_integer(self, oid: str, value: int) -> None:
        """SET an integer OID using the write community."""
        engine = await self._engine_ready()
        target = await self._target()
        err_indication, err_status, err_index, var_binds = await set_cmd(
            engine,
            CommunityData(self.write_community, mpModel=0),
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid), value),
        )
        if err_indication:
            raise HomeAssistantError(f"SNMP SET failed: {err_indication}")
        if err_status:
            raise HomeAssistantError(
                f"SNMP SET status {err_status.prettyPrint()} at {err_index}: {var_binds}"
            )

    async def reset_energy(self) -> None:
        """Reset device energy meter via SNMP."""
        await self.set_integer(OID_RESET_ENERGY, SNMP_RESET)

    async def reset_peak_power(self) -> None:
        """Reset peak power via SNMP."""
        await self.set_integer(OID_RESET_PEAK_POWER, SNMP_RESET)

    async def fetch_identity(self) -> dict[str, Any]:
        """Fetch identity fields used by config flow."""
        raw = await self.get_many(
            [OID_NAME, OID_MODEL, OID_SERIAL, OID_FIRMWARE, OID_LOCATION, OID_PROBE_COMM]
        )
        probe_comm = _as_int(raw.get(OID_PROBE_COMM))
        return {
            "name": _as_str(raw.get(OID_NAME)) or DEFAULT_NAME_SAFE,
            "model": _as_str(raw.get(OID_MODEL)),
            "serial": _as_str(raw.get(OID_SERIAL)),
            "firmware": _as_str(raw.get(OID_FIRMWARE)),
            "location": _as_str(raw.get(OID_LOCATION)),
            "has_env_probe": probe_comm not in (None, 1),
        }


# Avoid circular import of DEFAULT_NAME in identity helper
DEFAULT_NAME_SAFE = "Rack PDU"


class ApcRackPduCoordinator(DataUpdateCoordinator[PduData]):
    """Poll APC Metered Rack PDU telemetry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ApcRackPduClient) -> None:
        self.client = client
        self.entry = entry
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()),
        )
        try:
            update_interval = timedelta(seconds=int(interval))
        except (TypeError, ValueError):
            update_interval = DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_HOST]}",
            update_interval=update_interval,
            config_entry=entry,
        )

    async def _async_update_data(self) -> PduData:
        core_oids = [
            OID_NAME,
            OID_LOCATION,
            OID_MODEL,
            OID_SERIAL,
            OID_FIRMWARE,
            OID_NUM_OUTLETS,
            OID_MAX_CURRENT,
            OID_LOAD_STATE,
            OID_POWER,
            OID_PEAK_POWER,
            OID_ENERGY,
            OID_POWER_FACTOR,
            OID_PHASE_LOAD_STATE,
            OID_PHASE_CURRENT,
            OID_PHASE_VOLTAGE,
            OID_PHASE_POWER,
            OID_PHASE_APPARENT,
            OID_PHASE_PF,
            OID_PHASE_PEAK_CURRENT,
        ]
        raw = await self.client.get_many(core_oids)

        env_raw: dict[str, Any] = {}
        try:
            env_raw = await self.client.get_many(
                [OID_PROBE_NAME, OID_PROBE_COMM, OID_TEMP_F, OID_TEMP_C, OID_HUMIDITY]
            )
        except UpdateFailed:
            _LOGGER.debug("Env probe OIDs unavailable on %s", self.client.host)

        load_raw = _as_int(raw.get(OID_LOAD_STATE))
        phase_load_raw = _as_int(raw.get(OID_PHASE_LOAD_STATE))
        max_current = _as_int(raw.get(OID_MAX_CURRENT))
        current_a = _tenths_to_float(_as_int(raw.get(OID_PHASE_CURRENT)))
        load_percent = None
        if current_a is not None and max_current and max_current > 0:
            load_percent = round((current_a / float(max_current)) * 100.0, 1)

        probe_comm = _as_int(env_raw.get(OID_PROBE_COMM))
        has_probe = self.entry.options.get(
            CONF_HAS_ENV_PROBE, self.entry.data.get(CONF_HAS_ENV_PROBE)
        )
        if has_probe is None:
            has_probe = probe_comm not in (None, 1) and _as_int(env_raw.get(OID_TEMP_F)) is not None
        else:
            has_probe = bool(has_probe)

        temp_f = _tenths_to_float(_as_int(env_raw.get(OID_TEMP_F))) if has_probe else None
        temp_c = _tenths_to_float(_as_int(env_raw.get(OID_TEMP_C))) if has_probe else None
        humidity = _as_int(env_raw.get(OID_HUMIDITY)) if has_probe else None
        humidity_f = float(humidity) if humidity is not None and humidity >= 0 else None

        return PduData(
            name=_as_str(raw.get(OID_NAME)),
            location=_as_str(raw.get(OID_LOCATION)),
            model=_as_str(raw.get(OID_MODEL)),
            serial=_as_str(raw.get(OID_SERIAL)),
            firmware=_as_str(raw.get(OID_FIRMWARE)),
            num_outlets=_as_int(raw.get(OID_NUM_OUTLETS)),
            max_current=float(max_current) if max_current else None,
            load_state=LOAD_STATE_MAP.get(load_raw) if load_raw else None,
            load_state_raw=load_raw,
            power_w=_hundredths_kw_to_w(_as_int(raw.get(OID_POWER))),
            peak_power_w=_hundredths_kw_to_w(_as_int(raw.get(OID_PEAK_POWER))),
            energy_kwh=_tenths_to_float(_as_int(raw.get(OID_ENERGY))),
            power_factor=_hundredths_to_ratio(_as_int(raw.get(OID_POWER_FACTOR))),
            phase_load_state=LOAD_STATE_MAP.get(phase_load_raw) if phase_load_raw else None,
            current_a=current_a,
            voltage_v=float(v)
            if (v := _as_int(raw.get(OID_PHASE_VOLTAGE))) is not None and v >= 0
            else None,
            phase_power_w=_hundredths_kw_to_w(_as_int(raw.get(OID_PHASE_POWER))),
            apparent_power_va=_hundredths_kw_to_w(_as_int(raw.get(OID_PHASE_APPARENT))),
            phase_power_factor=_hundredths_to_ratio(_as_int(raw.get(OID_PHASE_PF))),
            peak_current_a=_tenths_to_float(_as_int(raw.get(OID_PHASE_PEAK_CURRENT))),
            load_percent=load_percent,
            has_env_probe=bool(has_probe),
            probe_name=_as_str(env_raw.get(OID_PROBE_NAME)) if has_probe else None,
            temperature_f=temp_f,
            temperature_c=temp_c,
            humidity=humidity_f,
        )

    def device_info_attrs(self) -> dict[str, Any]:
        """Attributes useful for DeviceInfo."""
        data = self.data
        return {
            ATTR_SERIAL: data.serial if data else None,
            ATTR_MODEL: data.model if data else None,
            ATTR_FIRMWARE: data.firmware if data else None,
            ATTR_LOCATION: data.location if data else None,
            ATTR_NUM_OUTLETS: data.num_outlets if data else None,
            ATTR_MAX_CURRENT: data.max_current if data else None,
        }
