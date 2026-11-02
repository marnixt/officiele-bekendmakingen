"""Map entities for Officiële Bekendmakingen."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ZONE, DOMAIN, MAX_MAP_ITEMS
from .coordinator import (
    BekendmakingenConfigEntry,
    BekendmakingenCoordinator,
    NearbyBekendmaking,
    publication_icon,
)

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
        new = []
        for key, nearby in current.items():
            if key in entities:
                entities[key].nearby = nearby
            else:
                entities[key] = PublicationEvent(coordinator, key, nearby)
                new.append(entities[key])
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
    _attr_translation_key = "publication"

    def __init__(
        self, coordinator: BekendmakingenCoordinator, unique_id: str, nearby: NearbyBekendmaking
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self.nearby = nearby

    @property
    def nearby(self) -> NearbyBekendmaking:
        return self._nearby

    @nearby.setter
    def nearby(self, nearby: NearbyBekendmaking) -> None:
        """Take over the latest data of the publication (e.g. a changed reaction deadline)."""
        self._nearby = nearby
        self._attr_name = nearby.item.title
        self._attr_icon = publication_icon(nearby.item)
        self._attr_latitude, self._attr_longitude = nearby.location
        self._attr_distance = nearby.distance_m / 1000

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **self._nearby.as_dict(self.coordinator.summary(self._nearby.item.identifier)),
            "zone": self.coordinator.config_entry.data[CONF_ZONE],
        }
