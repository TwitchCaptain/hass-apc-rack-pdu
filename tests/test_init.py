"""Setup, unload, and entity tests for apc_rack_pdu."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er

from custom_components.apc_rack_pdu.const import DOMAIN

from .conftest import SERIAL


async def test_setup_creates_entities(hass, setup_entry):
    assert setup_entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.values()
        if e.config_entry_id == setup_entry.entry_id
    ]
    unique_ids = {e.unique_id for e in entities}

    assert f"{SERIAL}_power" in unique_ids
    assert f"{SERIAL}_energy" in unique_ids
    assert f"{SERIAL}_temperature" in unique_ids
    assert f"{SERIAL}_humidity" in unique_ids
    assert f"{SERIAL}_overload" in unique_ids
    assert f"{SERIAL}_near_overload" in unique_ids
    assert f"{SERIAL}_reset_energy" in unique_ids
    assert f"{SERIAL}_reset_peak_power" in unique_ids
    assert f"{SERIAL}_identify" in unique_ids

    state = hass.states.get("sensor.rack_pdu_power")
    assert state is not None
    assert float(state.state) == 450.0


async def test_unload_entry(hass, setup_entry):
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED
    assert setup_entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_reset_energy_button(hass, setup_entry, mock_client):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "button", DOMAIN, f"{SERIAL}_reset_energy"
    )
    assert entity_id

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id},
        blocking=True,
    )
    mock_client.reset_energy.assert_awaited_once()
