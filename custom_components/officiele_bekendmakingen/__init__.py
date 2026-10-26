"""The Officiële Bekendmakingen integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_VERSION
from .coordinator import BekendmakingenConfigEntry, BekendmakingenCoordinator, storage_key

PLATFORMS: list[Platform] = [Platform.GEO_LOCATION, Platform.SENSOR]


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
    """Remove the stored list of announced publications."""
    await Store(hass, STORAGE_VERSION, storage_key(entry)).async_remove()
