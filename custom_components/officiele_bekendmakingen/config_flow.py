"""Config flow for Officiële Bekendmakingen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_AUTHORITIES,
    CONF_DAYS,
    CONF_RADIUS,
    CONF_ZONE,
    DEFAULT_DAYS,
    DEFAULT_RADIUS,
    DEFAULT_ZONE,
    DOMAIN,
)
from .locatieserver import Authority, LocatieserverError, async_authorities_near

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE, default=DEFAULT_ZONE): EntitySelector(
            EntitySelectorConfig(domain="zone")
        ),
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


def authority_options(authorities: list[Authority]) -> list[SelectOptionDict]:
    """Selector options for the authorities, with the distance for those outside the zone."""
    return [
        SelectOptionDict(
            value=a.name,
            label=a.label if a.distance_m == 0 else f"{a.label} ({a.distance_m / 1000:.1f} km)",
        )
        for a in authorities
    ]


class BekendmakingenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Officiële Bekendmakingen."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._title = ""
        self._authorities: list[Authority] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the zone, radius and look-back period."""
        errors: dict[str, str] = {}
        if user_input is not None:
            zone = user_input[CONF_ZONE]
            await self.async_set_unique_id(zone)
            self._abort_if_unique_id_configured()

            state = self.hass.states.get(zone)
            radius = int(user_input[CONF_RADIUS])
            if state is None or ATTR_LATITUDE not in state.attributes:
                errors[CONF_ZONE] = "invalid_zone"
            else:
                try:
                    self._authorities = await async_authorities_near(
                        async_get_clientsession(self.hass),
                        state.attributes[ATTR_LATITUDE],
                        state.attributes[ATTR_LONGITUDE],
                        radius,
                    )
                except LocatieserverError:
                    errors["base"] = "cannot_connect"
                else:
                    if not self._authorities:
                        errors[CONF_ZONE] = "no_authorities_found"
                    else:
                        self._title = state.name
                        self._data = {
                            CONF_ZONE: zone,
                            CONF_RADIUS: radius,
                            CONF_DAYS: int(user_input[CONF_DAYS]),
                        }
                        return await self.async_step_authorities()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_authorities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose which of the authorities around the zone to follow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_AUTHORITIES]:
                return self.async_create_entry(
                    title=self._title,
                    data={**self._data, CONF_AUTHORITIES: user_input[CONF_AUTHORITIES]},
                )
            errors[CONF_AUTHORITIES] = "no_authorities_selected"

        # Preselect the authorities whose area contains the zone itself.
        default = [a.name for a in self._authorities if a.distance_m == 0]
        schema = vol.Schema(
            {
                vol.Required(CONF_AUTHORITIES, default=default): SelectSelector(
                    SelectSelectorConfig(
                        options=authority_options(self._authorities),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="authorities",
            data_schema=schema,
            errors=errors,
            description_placeholders={"zone": self._title},
        )
