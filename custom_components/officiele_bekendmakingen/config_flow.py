"""Config flow for Officiële Bekendmakingen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .api import SruClient, SruError
from .const import (
    CONF_AUTHORITY,
    CONF_DAYS,
    CONF_RADIUS,
    DEFAULT_DAYS,
    DEFAULT_RADIUS,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTHORITY): TextSelector(),
        vol.Required(CONF_RADIUS, default=DEFAULT_RADIUS): NumberSelector(
            NumberSelectorConfig(
                min=100, max=20000, step=100, unit_of_measurement="m", mode=NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_DAYS, default=DEFAULT_DAYS): NumberSelector(
            NumberSelectorConfig(min=1, max=90, step=1, unit_of_measurement="d")
        ),
    }
)


class BekendmakingenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Officiële Bekendmakingen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            authority = user_input[CONF_AUTHORITY].strip()
            await self.async_set_unique_id(authority.casefold())
            self._abort_if_unique_id_configured()

            client = SruClient(async_get_clientsession(self.hass))
            try:
                count = await client.async_count(authority)
            except SruError:
                errors["base"] = "cannot_connect"
            else:
                if count == 0:
                    errors[CONF_AUTHORITY] = "unknown_authority"
                else:
                    return self.async_create_entry(
                        title=authority,
                        data={
                            CONF_AUTHORITY: authority,
                            CONF_RADIUS: int(user_input[CONF_RADIUS]),
                            CONF_DAYS: int(user_input[CONF_DAYS]),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )
