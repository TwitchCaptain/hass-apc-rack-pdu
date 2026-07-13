"""Config flow for APC Metered Rack PDU."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_COMMUNITY,
    CONF_HAS_ENV_PROBE,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_WRITE_COMMUNITY,
    DEFAULT_COMMUNITY,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WRITE_COMMUNITY,
    DOMAIN,
)
from .coordinator import ApcRackPduClient

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_COMMUNITY, default=DEFAULT_COMMUNITY): str,
        vol.Optional(CONF_WRITE_COMMUNITY, default=DEFAULT_WRITE_COMMUNITY): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(
            CONF_SCAN_INTERVAL, default=int(DEFAULT_SCAN_INTERVAL.total_seconds())
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for APC Metered Rack PDU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            client = ApcRackPduClient(
                self.hass,
                host=host,
                community=user_input.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
                write_community=user_input.get(
                    CONF_WRITE_COMMUNITY, DEFAULT_WRITE_COMMUNITY
                ),
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
            )
            try:
                identity = await client.fetch_identity()
            except Exception:  # noqa: BLE001 - surface as form error
                errors["base"] = "cannot_connect"
            else:
                serial = identity.get("serial") or host
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()

                title = user_input.get(CONF_NAME) or identity.get("name") or DEFAULT_NAME

                data = {
                    CONF_HOST: host,
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                    CONF_COMMUNITY: user_input.get(CONF_COMMUNITY, DEFAULT_COMMUNITY),
                    CONF_WRITE_COMMUNITY: user_input.get(
                        CONF_WRITE_COMMUNITY, DEFAULT_WRITE_COMMUNITY
                    ),
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
                    ),
                    CONF_HAS_ENV_PROBE: bool(identity.get("has_env_probe")),
                }
                if user_input.get(CONF_USERNAME):
                    data[CONF_USERNAME] = user_input[CONF_USERNAME]
                if user_input.get(CONF_PASSWORD):
                    data[CONF_PASSWORD] = user_input[CONF_PASSWORD]

                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(
                        CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(
                    CONF_HAS_ENV_PROBE,
                    default=current.get(CONF_HAS_ENV_PROBE, True),
                ): bool,
                vol.Optional(
                    CONF_WRITE_COMMUNITY,
                    default=current.get(CONF_WRITE_COMMUNITY, DEFAULT_WRITE_COMMUNITY),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
