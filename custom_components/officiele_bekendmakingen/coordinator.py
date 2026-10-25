"""Data update coordinator for Officiële Bekendmakingen."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance

from .api import Bekendmaking, SruClient, SruError
from .const import (
    CONF_AUTHORITY,
    CONF_DAYS,
    CONF_RADIUS,
    DEFAULT_DAYS,
    DEFAULT_RADIUS,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type BekendmakingenConfigEntry = ConfigEntry[BekendmakingenCoordinator]


@dataclass(frozen=True)
class NearbyBekendmaking:
    """A publication together with its distance to the home zone."""

    item: Bekendmaking
    distance_m: float | None


class BekendmakingenCoordinator(DataUpdateCoordinator[list[NearbyBekendmaking]]):
    """Fetch publications and keep the ones within the configured radius."""

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

    def _setting(self, key: str, default: int) -> int:
        return int(self.config_entry.options.get(key, self.config_entry.data.get(key, default)))

    def _distance(self, item: Bekendmaking) -> float | None:
        distances = [
            d
            for lat, lon in item.locations
            if (d := distance(self.hass.config.latitude, self.hass.config.longitude, lat, lon))
            is not None
        ]
        return min(distances, default=None)

    async def _async_update_data(self) -> list[NearbyBekendmaking]:
        since = dt_util.now().date() - timedelta(days=self._setting(CONF_DAYS, DEFAULT_DAYS))
        try:
            items = await self._client.async_search(
                self.config_entry.data[CONF_AUTHORITY], since
            )
        except SruError as err:
            raise UpdateFailed(str(err)) from err

        radius = self._setting(CONF_RADIUS, DEFAULT_RADIUS)
        nearby = [
            NearbyBekendmaking(item, dist)
            for item in items
            if (dist := self._distance(item)) is not None and dist <= radius
        ]
        nearby.sort(key=lambda n: n.distance_m or 0)
        return nearby
