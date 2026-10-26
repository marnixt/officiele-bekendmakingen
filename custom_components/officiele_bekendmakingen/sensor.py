"""Sensors for Officiële Bekendmakingen."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MAX_ATTRIBUTE_ITEMS
from .coordinator import BekendmakingenConfigEntry, BekendmakingenCoordinator, NearbyBekendmaking


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BekendmakingenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [NearbyCountSensor(coordinator), NextReactionDeadlineSensor(coordinator)]
    )


class BekendmakingenEntity(CoordinatorEntity[BekendmakingenCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BekendmakingenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Bekendmakingen {entry.title}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.officielebekendmakingen.nl",
        )


class NearbyCountSensor(BekendmakingenEntity, SensorEntity):
    """Number of publications within the radius; the closest ones as attributes."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _unrecorded_attributes = frozenset({"items"})

    def __init__(self, coordinator: BekendmakingenCoordinator) -> None:
        super().__init__(coordinator, "nearby")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"items": [n.as_dict() for n in self.coordinator.data[:MAX_ATTRIBUTE_ITEMS]]}


class NextReactionDeadlineSensor(BekendmakingenEntity, SensorEntity):
    """The first upcoming end of a reaction period within the radius."""

    _attr_device_class = SensorDeviceClass.DATE
    _unrecorded_attributes = frozenset({"items"})

    def __init__(self, coordinator: BekendmakingenCoordinator) -> None:
        super().__init__(coordinator, "next_reaction_deadline")

    def _open(self) -> list[NearbyBekendmaking]:
        today = dt_util.now().date()
        return sorted(
            (
                n
                for n in self.coordinator.data
                if n.item.reaction_deadline and n.item.reaction_deadline >= today
            ),
            key=lambda n: n.item.reaction_deadline,
        )

    @property
    def native_value(self) -> date | None:
        open_items = self._open()
        return open_items[0].item.reaction_deadline if open_items else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"items": [n.as_dict() for n in self._open()[:MAX_ATTRIBUTE_ITEMS]]}
