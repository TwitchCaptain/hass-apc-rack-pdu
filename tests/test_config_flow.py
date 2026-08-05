"""Tests for the apc_rack_pdu config and options flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.apc_rack_pdu.const import (
    CONF_HAS_ENV_PROBE,
    CONF_WRITE_COMMUNITY,
    DOMAIN,
)

from .conftest import SERIAL, USER_INPUT


def _patch_identity(result=None, side_effect=None):
    if result is None:
        result = {
            "name": "Rack PDU",
            "model": "AP8858",
            "serial": SERIAL,
            "firmware": "v1.0",
            "location": "Closet",
            "has_env_probe": True,
        }
    return patch(
        "custom_components.apc_rack_pdu.config_flow.ApcRackPduClient.fetch_identity",
        new=AsyncMock(return_value=result, side_effect=side_effect),
    )


def _patch_setup():
    return patch(
        "custom_components.apc_rack_pdu.async_setup_entry",
        return_value=True,
    )


async def test_user_flow_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with _patch_identity(), _patch_setup():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rack PDU"
    assert result["data"][CONF_HOST] == "pdu.local"
    assert result["data"][CONF_HAS_ENV_PROBE] is True
    assert result["result"].unique_id == SERIAL


async def test_user_flow_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with _patch_identity(side_effect=OSError("down")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_aborts_on_duplicate(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with _patch_identity():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_options(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    with _patch_setup():
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SCAN_INTERVAL: 60,
                CONF_HAS_ENV_PROBE: False,
                CONF_WRITE_COMMUNITY: "secret",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 60
    assert mock_config_entry.options[CONF_HAS_ENV_PROBE] is False
    assert mock_config_entry.options[CONF_WRITE_COMMUNITY] == "secret"
