"""The Officiële Bekendmakingen integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL_PATH, STORAGE_VERSION
from .coordinator import (
    BekendmakingenConfigEntry,
    BekendmakingenCoordinator,
    storage_key,
    summaries_storage_key,
)

PLATFORMS: list[Platform] = [Platform.GEO_LOCATION, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the map card and load it on every dashboard."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL_PATH, str(Path(__file__).parent / "frontend"), True)]
    )
    # The version in the URL makes browsers fetch the card again after an update.
    add_extra_js_url(hass, f"{FRONTEND_URL_PATH}/{CARD_FILENAME}?v={integration.version}")
    return True


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
    """Remove the stored announced publications and summaries."""
    for key in (storage_key(entry), summaries_storage_key(entry)):
        await Store(hass, STORAGE_VERSION, key).async_remove()
