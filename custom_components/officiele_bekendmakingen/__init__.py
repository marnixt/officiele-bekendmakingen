"""The Officiële Bekendmakingen integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import (
    ATTR_IDENTIFIER,
    CARD_FILENAME,
    DOMAIN,
    FRONTEND_URL_PATH,
    SERVICE_FOLLOW,
    SERVICE_UNFOLLOW,
    STORAGE_VERSION,
)
from .coordinator import (
    BekendmakingenConfigEntry,
    BekendmakingenCoordinator,
    follows_storage_key,
    storage_key,
    summaries_storage_key,
)

PLATFORMS: list[Platform] = [Platform.GEO_LOCATION, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FOLLOW_SCHEMA = vol.Schema({vol.Required(ATTR_IDENTIFIER): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the map card and load it on every dashboard."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL_PATH, str(Path(__file__).parent / "frontend"), True)]
    )
    # The version in the URL makes browsers fetch the card again after an update.
    add_extra_js_url(hass, f"{FRONTEND_URL_PATH}/{CARD_FILENAME}?v={integration.version}")

    async def _async_follow(call: ServiceCall) -> None:
        for coordinator in _coordinators_with(hass, call.data[ATTR_IDENTIFIER]):
            if call.service == SERVICE_FOLLOW:
                await coordinator.async_follow(call.data[ATTR_IDENTIFIER])
            else:
                await coordinator.async_unfollow(call.data[ATTR_IDENTIFIER])

    for service in (SERVICE_FOLLOW, SERVICE_UNFOLLOW):
        hass.services.async_register(DOMAIN, service, _async_follow, schema=FOLLOW_SCHEMA)
    return True


def _coordinators_with(hass: HomeAssistant, identifier: str) -> list[BekendmakingenCoordinator]:
    """Return the coordinators that have a publication within their radius."""
    coordinators = [
        entry.runtime_data
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if entry.runtime_data.has_publication(identifier)
    ]
    if not coordinators:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_publication",
            translation_placeholders={"identifier": identifier},
        )
    return coordinators


async def async_setup_entry(hass: HomeAssistant, entry: BekendmakingenConfigEntry) -> bool:
    """Set up Officiële Bekendmakingen from a config entry."""
    coordinator = BekendmakingenCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BekendmakingenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: BekendmakingenConfigEntry) -> None:
    """Remove the stored announced publications, summaries and followed addresses."""
    for key in (storage_key(entry), summaries_storage_key(entry), follows_storage_key(entry)):
        await Store(hass, STORAGE_VERSION, key).async_remove()
