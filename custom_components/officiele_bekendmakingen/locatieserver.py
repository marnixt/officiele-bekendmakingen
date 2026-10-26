"""Suggest publishing authorities near a location using the PDOK Locatieserver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import LOCATIESERVER_REVERSE_URL

_TIMEOUT = aiohttp.ClientTimeout(total=30)
# Field in a Locatieserver document that holds the authority name, per document type.
# These names match dt.creator in the SRU service.
_NAME_FIELDS = {
    "gemeente": "gemeentenaam",
    "provincie": "provincienaam",
    "waterschap": "waterschapsnaam",
}


class LocatieserverError(Exception):
    """Raised when the Locatieserver cannot be reached or returns an error."""


@dataclass(frozen=True)
class Authority:
    """A publishing authority whose area lies within some distance of a location."""

    name: str
    label: str
    distance_m: float


def parse_authorities(docs: list[dict[str, Any]]) -> list[Authority]:
    """Turn reverse-geocoding documents into authorities, closest first."""
    authorities: dict[str, Authority] = {}
    for doc in docs:
        field = _NAME_FIELDS.get(doc.get("type", ""))
        name = doc.get(field) if field else None
        if not name or name in authorities:
            continue
        authorities[name] = Authority(
            name=name,
            label=doc.get("weergavenaam") or name,
            distance_m=float(doc.get("afstand", 0)),
        )
    return sorted(authorities.values(), key=lambda a: (a.distance_m, a.label))


async def async_authorities_near(
    session: aiohttp.ClientSession, latitude: float, longitude: float, radius_m: int
) -> list[Authority]:
    """Return the municipalities, provinces and water boards within a radius of a location."""
    params = [
        ("lat", str(latitude)),
        ("lon", str(longitude)),
        ("distance", str(radius_m)),
        ("rows", "100"),
        ("fl", "type,gemeentenaam,provincienaam,waterschapsnaam,weergavenaam,afstand"),
        *(("type", t) for t in _NAME_FIELDS),
    ]
    try:
        async with session.get(LOCATIESERVER_REVERSE_URL, params=params, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            body = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise LocatieserverError(f"Cannot reach the PDOK Locatieserver: {err}") from err
    try:
        docs = body["response"]["docs"]
    except (KeyError, TypeError) as err:
        raise LocatieserverError("Unexpected Locatieserver response") from err
    return parse_authorities(docs)
