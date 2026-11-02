"""Config flow for Officiële Bekendmakingen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, callback
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
    CONF_AI_TASK_ENTITY,
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

RADIUS_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=100, max=20000, step=100, unit_of_measurement="m", mode=NumberSelectorMode.BOX
    )
)
DAYS_SELECTOR = NumberSelector(NumberSelectorConfig(min=1, max=90, step=1, unit_of_measurement="d"))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONE, default=DEFAULT_ZONE): EntitySelector(
            EntitySelectorConfig(domain="zone")
        ),
        vol.Required(CONF_RADIUS, default=DEFAULT_RADIUS): RADIUS_SELECTOR,
        vol.Required(CONF_DAYS, default=DEFAULT_DAYS): DAYS_SELECTOR,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_RADIUS): RADIUS_SELECTOR,
        vol.Required(CONF_DAYS): DAYS_SELECTOR,
        vol.Optional(CONF_AI_TASK_ENTITY): EntitySelector(EntitySelectorConfig(domain="ai_task")),
    }
)


async def async_lookup_authorities(
    hass: HomeAssistant, zone: str, radius: int
) -> tuple[list[Authority], dict[str, str]]:
    """Return the authorities within the radius of a zone, or the form errors."""
    state = hass.states.get(zone)
    if state is None or ATTR_LATITUDE not in state.attributes:
        return [], {CONF_ZONE: "invalid_zone"}
    try:
        authorities = await async_authorities_near(
            async_get_clientsession(hass),
            state.attributes[ATTR_LATITUDE],
            state.attributes[ATTR_LONGITUDE],
            radius,
        )
    except LocatieserverError:
        return [], {"base": "cannot_connect"}
    if not authorities:
        return [], {CONF_ZONE: "no_authorities_found"}
    return authorities, {}


def authorities_schema(options: list[SelectOptionDict], default: list[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_AUTHORITIES, default=default): SelectSelector(
                SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
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

            radius = int(user_input[CONF_RADIUS])
            self._authorities, errors = await async_lookup_authorities(self.hass, zone, radius)
            if not errors:
                self._title = self.hass.states.get(zone).name
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
        schema = authorities_schema(authority_options(self._authorities), default)
        return self.async_show_form(
            step_id="authorities",
            data_schema=schema,
            errors=errors,
            description_placeholders={"zone": self._title},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BekendmakingenOptionsFlow:
        return BekendmakingenOptionsFlow()


class BekendmakingenOptionsFlow(OptionsFlowWithReload):
    """Change the radius, look-back period, authorities and AI summaries of a zone."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}
        self._authorities: list[Authority] = []

    def _current(self, key: str) -> Any:
        return self.config_entry.options.get(key, self.config_entry.data.get(key))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the radius, look-back period and the AI task entity for summaries."""
        errors: dict[str, str] = {}
        if user_input is not None:
            radius = int(user_input[CONF_RADIUS])
            self._authorities, errors = await async_lookup_authorities(
                self.hass, self.config_entry.data[CONF_ZONE], radius
            )
            # The zone cannot be changed here, so show zone errors for the whole form.
            errors = {"base" if key == CONF_ZONE else key: e for key, e in errors.items()}
            if not errors:
                self._options = {CONF_RADIUS: radius, CONF_DAYS: int(user_input[CONF_DAYS])}
                if user_input.get(CONF_AI_TASK_ENTITY):
                    self._options[CONF_AI_TASK_ENTITY] = user_input[CONF_AI_TASK_ENTITY]
                return await self.async_step_authorities()

        suggested = user_input or {
            key: value
            for key in (CONF_RADIUS, CONF_DAYS, CONF_AI_TASK_ENTITY)
            if (value := self._current(key)) is not None
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, suggested),
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
                    data={**self._options, CONF_AUTHORITIES: user_input[CONF_AUTHORITIES]}
                )
            errors[CONF_AUTHORITIES] = "no_authorities_selected"

        current = self._current(CONF_AUTHORITIES)
        options = authority_options(self._authorities)
        # Keep followed authorities that are now outside the radius, so they can be deselected.
        found = {a.name for a in self._authorities}
        options += [SelectOptionDict(value=a, label=a) for a in current if a not in found]
        return self.async_show_form(
            step_id="authorities",
            data_schema=authorities_schema(options, current),
            errors=errors,
            description_placeholders={"zone": self.config_entry.title},
        )
