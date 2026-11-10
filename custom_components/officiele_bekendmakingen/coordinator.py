"""Data update coordinator for Officiële Bekendmakingen."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance

from .api import Bekendmaking, SruClient, SruError
from .const import (
    ACTIVITEIT_ICONS,
    AI_WAIT_ATTEMPTS,
    AI_WAIT_INTERVAL,
    CONF_AI_TASK_ENTITY,
    CONF_AUTHORITIES,
    CONF_DAYS,
    CONF_RADIUS,
    CONF_SUMMARY_LANGUAGE,
    CONF_ZONE,
    DEFAULT_DAYS,
    DEFAULT_ICON,
    DEFAULT_RADIUS,
    DEFAULT_SUMMARY_LANGUAGE,
    DOMAIN,
    EVENT_NEW_PUBLICATION,
    MAX_ATTRIBUTE_ITEMS,
    MAX_MAP_ITEMS,
    MAX_SUMMARIES_PER_UPDATE,
    RUBRIEK_ICONS,
    SCAN_INTERVAL,
    SEEN_RETENTION,
    STORAGE_VERSION,
)
from .follow import Follow, follow_for, matches
from .summary import SummaryError, async_fetch_text, async_summarize

_LOGGER = logging.getLogger(__name__)

type BekendmakingenConfigEntry = ConfigEntry[BekendmakingenCoordinator]


@dataclass(frozen=True)
class NearbyBekendmaking:
    """A publication together with its distance to the zone."""

    item: Bekendmaking
    distance_m: float
    # (latitude, longitude) of the marked area closest to the zone.
    location: tuple[float, float]

    def as_dict(
        self,
        summary: dict[str, str] | None = None,
        first_seen: str | None = None,
        followed: bool = False,
    ) -> dict[str, Any]:
        """Return the publication as attributes, with what the integration knows about it.

        first_seen is when the integration first found it; followed tells whether it is
        about a followed address.
        """
        item = self.item
        summary = summary or {}
        return {
            "identifier": item.identifier,
            "title": item.title,
            "address": item.address,
            "rubriek": item.rubriek,
            "activiteit": item.activiteit,
            "abstract": item.abstract,
            "authority": item.authority,
            "published": item.published.isoformat() if item.published else None,
            "reaction_deadline": (
                item.reaction_deadline.isoformat() if item.reaction_deadline else None
            ),
            "distance_m": round(self.distance_m),
            "url": item.url,
            "summary": summary.get("summary"),
            "impact": summary.get("impact"),
            "first_seen": first_seen,
            "followed": followed,
        }


def publication_icon(item: Bekendmaking) -> str:
    """Return the icon for a publication, by activity first and rubriek second."""
    if item.activiteit in ACTIVITEIT_ICONS:
        return ACTIVITEIT_ICONS[item.activiteit]
    return RUBRIEK_ICONS.get(item.rubriek or "", DEFAULT_ICON)


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
    seen: dict[str, str], nearby: list[NearbyBekendmaking], now: datetime
) -> tuple[list[NearbyBekendmaking], dict[str, str]]:
    """Return the publications not seen before, and the seen map (id -> first seen) to store.

    First seen is an ISO timestamp; ISO strings sort in time order, so they compare as text.
    """
    new = [n for n in nearby if n.item.identifier not in seen]
    keep_from = (now - SEEN_RETENTION).isoformat()
    updated = {key: first for key, first in seen.items() if first >= keep_from}
    first_seen = now.isoformat(timespec="seconds")
    updated.update({n.item.identifier: first_seen for n in new})
    return new, updated


def needs_summary(
    summaries: dict[str, dict[str, str]], identifier: str, language: str
) -> bool:
    """Return whether a publication has no summary yet, or one in another language."""
    return summaries.get(identifier, {}).get("language") != language


def summary_backlog(
    nearby: list[NearbyBekendmaking], summaries: dict[str, dict[str, str]], language: str
) -> list[NearbyBekendmaking]:
    """Return the publications on the map that still need a summary, closest first."""
    missing = [
        n for n in nearby[:MAX_MAP_ITEMS] if needs_summary(summaries, n.item.identifier, language)
    ]
    return missing[:MAX_SUMMARIES_PER_UPDATE]


def storage_key(entry: ConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}"


def summaries_storage_key(entry: ConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}.summaries"


def follows_storage_key(entry: ConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}.follows"


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
        self._session = async_get_clientsession(hass)
        self._client = SruClient(self._session)
        self._store: Store[dict[str, str]] = Store(hass, STORAGE_VERSION, storage_key(entry))
        # Identifiers of publications already announced; None until loaded from the store.
        self._seen: dict[str, str] | None = None
        self._summary_store: Store[dict[str, dict[str, str]]] = Store(
            hass, STORAGE_VERSION, summaries_storage_key(entry)
        )
        # AI summaries by identifier; None until loaded from the store.
        self._summaries: dict[str, dict[str, str]] | None = None
        self._follow_store: Store[list[dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, follows_storage_key(entry)
        )
        # Followed addresses; None until loaded from the store.
        self._follows: list[Follow] | None = None
        # New publications waiting to be summarised and announced by the worker.
        self._pending: list[NearbyBekendmaking] = []
        self._latest: list[NearbyBekendmaking] = []
        self._worker: asyncio.Task[None] | None = None

    def _setting(self, key: str, default: Any = None) -> Any:
        return self.config_entry.options.get(key, self.config_entry.data.get(key, default))

    @property
    def ai_task_entity(self) -> str | None:
        """The AI task entity that writes summaries, if one is configured."""
        return self._setting(CONF_AI_TASK_ENTITY)

    @property
    def summary_language(self) -> str:
        return self._setting(CONF_SUMMARY_LANGUAGE, DEFAULT_SUMMARY_LANGUAGE)

    def summary(self, identifier: str) -> dict[str, str] | None:
        """Return the AI summary of a publication, if there is one."""
        return (self._summaries or {}).get(identifier)

    def is_followed(self, nearby: NearbyBekendmaking) -> bool:
        """Return whether a publication is about a followed address."""
        return any(matches(follow, nearby) for follow in self._follows or ())

    def attributes(self, nearby: NearbyBekendmaking) -> dict[str, Any]:
        """Return a publication with its summary, first seen time and followed state."""
        identifier = nearby.item.identifier
        return nearby.as_dict(
            self.summary(identifier),
            (self._seen or {}).get(identifier),
            self.is_followed(nearby),
        )

    def items_as_dicts(self, nearby: list[NearbyBekendmaking]) -> list[dict[str, Any]]:
        """Return the first publications, with their summaries, for a sensor attribute."""
        return [self.attributes(n) for n in nearby[:MAX_ATTRIBUTE_ITEMS]]

    def _find(self, identifier: str) -> NearbyBekendmaking | None:
        return next((n for n in self.data or () if n.item.identifier == identifier), None)

    def has_publication(self, identifier: str) -> bool:
        return self._find(identifier) is not None

    async def async_follow(self, identifier: str) -> None:
        """Follow the address of a publication within the radius."""
        nearby = self._find(identifier)
        if nearby is None or self._follows is None or self.is_followed(nearby):
            return
        self._follows.append(follow_for(nearby))
        await self._async_save_follows()

    async def async_unfollow(self, identifier: str) -> None:
        """Stop following every address that a publication within the radius belongs to."""
        nearby = self._find(identifier)
        if nearby is None or self._follows is None or not self.is_followed(nearby):
            return
        self._follows = [f for f in self._follows if not matches(f, nearby)]
        await self._async_save_follows()

    async def _async_save_follows(self) -> None:
        assert self._follows is not None
        await self._follow_store.async_save([f.as_dict() for f in self._follows])
        self.async_update_listeners()

    def _zone_location(self) -> tuple[float, float]:
        zone = self.config_entry.data[CONF_ZONE]
        state = self.hass.states.get(zone)
        if state is None:
            raise UpdateFailed(f"Zone {zone} does not exist")
        return state.attributes[ATTR_LATITUDE], state.attributes[ATTR_LONGITUDE]

    async def _async_update_data(self) -> list[NearbyBekendmaking]:
        home = self._zone_location()
        since = dt_util.now().date() - timedelta(days=int(self._setting(CONF_DAYS, DEFAULT_DAYS)))
        try:
            items = await self._client.async_search(self._setting(CONF_AUTHORITIES), since)
        except SruError as err:
            raise UpdateFailed(str(err)) from err

        radius = int(self._setting(CONF_RADIUS, DEFAULT_RADIUS))
        nearby = []
        for item in items:
            closest = nearest_location(home, item.locations)
            if closest is not None and closest[0] <= radius:
                nearby.append(NearbyBekendmaking(item, *closest))
        nearby.sort(key=lambda n: n.distance_m)
        if self._summaries is None:
            self._summaries = await self._summary_store.async_load() or {}
        if self._follows is None:
            stored_follows = await self._follow_store.async_load() or []
            self._follows = [Follow.from_dict(f) for f in stored_follows]
        self._pending.extend(await self._update_seen(nearby))
        self._latest = nearby
        if self._worker is None or self._worker.done():
            self._worker = self.config_entry.async_create_background_task(
                self.hass, self._async_work(), f"{DOMAIN} summaries"
            )
        return nearby

    async def _update_seen(self, nearby: list[NearbyBekendmaking]) -> list[NearbyBekendmaking]:
        """Return the publications to announce: the ones not seen before."""
        if self._seen is None:
            stored = await self._store.async_load()
            # On the very first run everything is new; record it without announcing.
            first_run = stored is None
            self._seen = stored or {}
        else:
            first_run = False

        new, seen = update_seen(self._seen, nearby, dt_util.now())
        if first_run or seen != self._seen:
            await self._store.async_save(seen)
        self._seen = seen
        return [] if first_run else new

    async def _async_work(self) -> None:
        """Summarise and announce new publications, then catch up on older ones."""
        assert self._summaries is not None
        entity_id = self.ai_task_entity
        if entity_id is not None and not await self._async_ai_available(entity_id):
            _LOGGER.warning(
                "AI task %s is not available; no summaries until the next update", entity_id
            )
            entity_id = None
        changed = False
        while True:
            while self._pending:
                nearby = self._pending.pop(0)
                changed |= await self._async_summarize(entity_id, nearby.item)
                self._announce(nearby)
            if entity_id is not None:
                for nearby in summary_backlog(self._latest, self._summaries, self.summary_language):
                    if self._pending:
                        break  # announce publications that came in meanwhile first
                    changed |= await self._async_summarize(entity_id, nearby.item)
            if not self._pending:
                break

        # Forget summaries of publications that are no longer within the radius.
        current = {n.item.identifier for n in self._latest}
        if self._summaries.keys() - current:
            self._summaries = {k: v for k, v in self._summaries.items() if k in current}
            changed = True
        if changed:
            await self._summary_store.async_save(self._summaries)
            self.async_update_listeners()

    async def _async_ai_available(self, entity_id: str) -> bool:
        """Wait a while for the AI task entity, which may still be starting up."""
        for attempt in range(AI_WAIT_ATTEMPTS):
            state = self.hass.states.get(entity_id)
            if state is not None and state.state != STATE_UNAVAILABLE:
                return True
            if attempt < AI_WAIT_ATTEMPTS - 1:
                await asyncio.sleep(AI_WAIT_INTERVAL)
        return False

    async def _async_summarize(self, entity_id: str | None, item: Bekendmaking) -> bool:
        """Summarise a publication with the AI task entity, if any; return whether it worked."""
        assert self._summaries is not None
        language = self.summary_language
        if entity_id is None or not needs_summary(self._summaries, item.identifier, language):
            return False
        try:
            text = await async_fetch_text(self._session, item)
            self._summaries[item.identifier] = await async_summarize(
                self.hass, entity_id, item, text, language
            )
        except SummaryError as err:
            # Only the summary is missing; it is tried again on the next update.
            _LOGGER.warning("No summary for %s: %s", item.identifier, err)
            return False
        return True

    def _announce(self, nearby: NearbyBekendmaking) -> None:
        self.hass.bus.async_fire(
            EVENT_NEW_PUBLICATION,
            {
                "entry_id": self.config_entry.entry_id,
                "zone": self.config_entry.data[CONF_ZONE],
                **self.attributes(nearby),
            },
        )
