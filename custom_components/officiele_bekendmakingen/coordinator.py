"""Data update coordinator for Officiële Bekendmakingen."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance

from .api import Bekendmaking, SruClient, SruError
from .const import (
    CONF_AUTHORITIES,
    CONF_DAYS,
    CONF_RADIUS,
    CONF_ZONE,
    DEFAULT_DAYS,
    DEFAULT_RADIUS,
    DOMAIN,
    EVENT_NEW_PUBLICATION,
    SCAN_INTERVAL,
    SEEN_RETENTION,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

type BekendmakingenConfigEntry = ConfigEntry[BekendmakingenCoordinator]


@dataclass(frozen=True)
class NearbyBekendmaking:
    """A publication together with its distance to the zone."""

    item: Bekendmaking
    distance_m: float
    # (latitude, longitude) of the marked area closest to the zone.
    location: tuple[float, float]

    def as_dict(self) -> dict[str, Any]:
        """Return the publication as entity attributes."""
        item = self.item
        return {
            "title": item.title,
            "rubriek": item.rubriek,
            "activiteit": item.activiteit,
            "authority": item.authority,
            "published": item.published.isoformat() if item.published else None,
            "reaction_deadline": (
                item.reaction_deadline.isoformat() if item.reaction_deadline else None
            ),
            "distance_m": round(self.distance_m),
            "url": item.url,
        }


def nearest_location(
    home: tuple[float, float], locations: tuple[tuple[float, float], ...]
) -> tuple[float, tuple[float, float]] | None:
    """Return the distance in metres to, and the position of, the location closest to home."""
    candidates = [
        (d, location)
        for location in locations
        if (d := distance(home[0], home[1], location[0], location[1])) is not None
    ]
    return min(candidates, key=lambda c: c[0], default=None)


def update_seen(
    seen: dict[str, str], nearby: list[NearbyBekendmaking], today: date
) -> tuple[list[NearbyBekendmaking], dict[str, str]]:
    """Return the publications not seen before, and the seen map (id -> first seen) to store."""
    new = [n for n in nearby if n.item.identifier not in seen]
    keep_from = (today - SEEN_RETENTION).isoformat()
    updated = {key: first for key, first in seen.items() if first >= keep_from}
    updated.update({n.item.identifier: today.isoformat() for n in new})
    return new, updated


def storage_key(entry: ConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}"


class BekendmakingenCoordinator(DataUpdateCoordinator[list[NearbyBekendmaking]]):
    """Fetch publications and keep the ones within the configured radius of the zone."""

    config_entry: BekendmakingenConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BekendmakingenConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self._client = SruClient(async_get_clientsession(hass))
        self._store: Store[dict[str, str]] = Store(hass, STORAGE_VERSION, storage_key(entry))
        # Identifiers of publications already announced; None until loaded from the store.
        self._seen: dict[str, str] | None = None

    def _setting(self, key: str, default: int) -> int:
        return int(self.config_entry.options.get(key, self.config_entry.data.get(key, default)))

    def _zone_location(self) -> tuple[float, float]:
        zone = self.config_entry.data[CONF_ZONE]
        state = self.hass.states.get(zone)
        if state is None:
            raise UpdateFailed(f"Zone {zone} does not exist")
        return state.attributes[ATTR_LATITUDE], state.attributes[ATTR_LONGITUDE]

    async def _async_update_data(self) -> list[NearbyBekendmaking]:
        home = self._zone_location()
        since = dt_util.now().date() - timedelta(days=self._setting(CONF_DAYS, DEFAULT_DAYS))
        try:
            items = await self._client.async_search(
                self.config_entry.data[CONF_AUTHORITIES], since
            )
        except SruError as err:
            raise UpdateFailed(str(err)) from err

        radius = self._setting(CONF_RADIUS, DEFAULT_RADIUS)
        nearby = []
        for item in items:
            closest = nearest_location(home, item.locations)
            if closest is not None and closest[0] <= radius:
                nearby.append(NearbyBekendmaking(item, *closest))
        nearby.sort(key=lambda n: n.distance_m)
        await self._announce(nearby)
        return nearby

    async def _announce(self, nearby: list[NearbyBekendmaking]) -> None:
        """Fire an event for every publication that was not seen before."""
        if self._seen is None:
            stored = await self._store.async_load()
            # On the very first run everything is new; record it without announcing.
            first_run = stored is None
            self._seen = stored or {}
        else:
            first_run = False

        new, seen = update_seen(self._seen, nearby, dt_util.now().date())
        if not first_run:
            for n in new:
                self.hass.bus.async_fire(
                    EVENT_NEW_PUBLICATION,
                    {
                        "entry_id": self.config_entry.entry_id,
                        "zone": self.config_entry.data[CONF_ZONE],
                        "identifier": n.item.identifier,
                        **n.as_dict(),
                    },
                )
        if first_run or seen != self._seen:
            await self._store.async_save(seen)
        self._seen = seen
