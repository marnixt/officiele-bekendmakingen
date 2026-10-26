"""Map entities for Officiële Bekendmakingen."""

from __future__ import annotations

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_MAP_ITEMS
from .coordinator import BekendmakingenConfigEntry, BekendmakingenCoordinator, NearbyBekendmaking

PLATFORM_DOMAIN = "geo_location"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BekendmakingenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one entity per nearby publication, adding and removing them as the data changes."""
    coordinator = entry.runtime_data
    registry = er.async_get(hass)
    entities: dict[str, PublicationEvent] = {}

    def _current() -> dict[str, NearbyBekendmaking]:
        return {_unique_id(entry, n): n for n in coordinator.data[:MAX_MAP_ITEMS]}

    # Publications that dropped out while Home Assistant was not running.
    current = _current()
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.domain == PLATFORM_DOMAIN and reg_entry.unique_id not in current:
            registry.async_remove(reg_entry.entity_id)

    @callback
    def _sync() -> None:
        current = _current()
        for key in entities.keys() - current.keys():
            entity = entities.pop(key)
            # Removing the registry entry also removes the entity from the state machine.
            if entity.entity_id and registry.async_get(entity.entity_id):
                registry.async_remove(entity.entity_id)
        new = [
            PublicationEvent(coordinator, key, n)
            for key, n in current.items()
            if key not in entities
        ]
        for entity in new:
            entities[entity.unique_id] = entity
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


def _unique_id(entry: BekendmakingenConfigEntry, nearby: NearbyBekendmaking) -> str:
    return f"{entry.entry_id}_{nearby.item.identifier}"


class PublicationEvent(CoordinatorEntity[BekendmakingenCoordinator], GeolocationEvent):
    """A publication within the radius, shown on the map at its closest location."""

    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:file-document-outline"

    def __init__(
        self, coordinator: BekendmakingenCoordinator, unique_id: str, nearby: NearbyBekendmaking
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = nearby.item.title
        self._attr_latitude, self._attr_longitude = nearby.location
        self._attr_distance = nearby.distance_m / 1000
        self._attr_extra_state_attributes = nearby.as_dict()
