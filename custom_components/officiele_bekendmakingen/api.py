"""Client for the SRU search service of officielebekendmakingen.nl."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date

import aiohttp

from .const import SRU_PAGE_SIZE, SRU_URL

NS = {
    "sru": "http://docs.oasis-open.org/ns/search-ws/sruResponse",
    "gzd": "http://standaarden.overheid.nl/sru",
    "dcterms": "http://purl.org/dc/terms/",
    "ow": "http://standaarden.overheid.nl/wetgeving/",
}

_COORD_PAIR = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)")
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class SruError(Exception):
    """Raised when the SRU service cannot be reached or returns an error."""


@dataclass(frozen=True)
class Bekendmaking:
    """A single official publication."""

    identifier: str
    title: str
    authority: str | None
    rubriek: str | None
    activiteit: str | None
    published: date | None
    reaction_deadline: date | None
    url: str | None
    # (latitude, longitude) of each marked area, as WGS84 centroids.
    locations: tuple[tuple[float, float], ...] = field(default_factory=tuple)
    # Short description that some authorities add, e.g. "vervangen van de dakkapel".
    abstract: str | None = None
    # The full text as XML; only fetched for AI summaries.
    content_url: str | None = None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def wkt_centroid(wkt: str) -> tuple[float, float] | None:
    """Return the (lat, lon) mean of all coordinates in a WGS84 WKT geometry.

    WKT lists coordinates as "lon lat". The mean of the vertices is close enough to the
    real centroid for the small areas that publications mark.
    """
    pairs = [(float(lon), float(lat)) for lon, lat in _COORD_PAIR.findall(wkt)]
    if not pairs:
        return None
    lon = sum(p[0] for p in pairs) / len(pairs)
    lat = sum(p[1] for p in pairs) / len(pairs)
    return lat, lon


def _text(element: ET.Element, path: str) -> str | None:
    found = element.find(path, NS)
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def parse_record(record: ET.Element) -> Bekendmaking | None:
    """Parse one sru:record element."""
    meta = record.find(".//ow:meta", NS)
    if meta is None:
        return None
    identifier = _text(meta, "ow:owmskern/dcterms:identifier")
    if identifier is None:
        return None
    locations = tuple(
        centroid
        for area in meta.iterfind(".//ow:locatiegebied", NS)
        if area.text and (centroid := wkt_centroid(area.text))
    )
    return Bekendmaking(
        identifier=identifier,
        title=_text(meta, "ow:owmskern/dcterms:title") or identifier,
        authority=_text(meta, "ow:owmskern/dcterms:creator"),
        rubriek=_text(meta, "ow:owmskern/dcterms:type"),
        activiteit=_text(meta, "ow:tpmeta/ow:activiteit"),
        published=_parse_date(_text(meta, "ow:owmsmantel/dcterms:date")),
        reaction_deadline=_parse_date(_text(meta, "ow:tpmeta/ow:datumEindeReactietermijn")),
        url=_text(record, ".//gzd:preferredUrl"),
        locations=locations,
        abstract=_text(meta, "ow:owmsmantel/dcterms:abstract"),
        content_url=_text(record, ".//gzd:enrichedData/gzd:url"),
    )


def parse_response(xml: str) -> tuple[int, list[Bekendmaking]]:
    """Parse an SRU response into (total number of records, parsed records)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as err:
        raise SruError(f"Invalid SRU response: {err}") from err
    total_text = _text(root, "sru:numberOfRecords")
    if total_text is None:
        # Errors come back as diagnostics instead of a result set.
        raise SruError("SRU response has no numberOfRecords")
    items = [
        item
        for record in root.iterfind("sru:records/sru:record", NS)
        if (item := parse_record(record)) is not None
    ]
    return int(total_text), items


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class SruClient:
    """Minimal async client for the SRU search service."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _request(self, query: str, start: int, size: int) -> tuple[int, list[Bekendmaking]]:
        params = {
            "query": query,
            "maximumRecords": str(size),
            "startRecord": str(start),
            "httpAccept": "application/xml",
        }
        try:
            async with self._session.get(SRU_URL, params=params, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                body = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SruError(f"Cannot reach SRU service: {err}") from err
        return parse_response(body)

    @staticmethod
    def _query(authorities: list[str], since: date | None = None) -> str:
        creators = " OR ".join(f"dt.creator=={_quote(a)}" for a in authorities)
        query = f"c.product-area==officielepublicaties AND ({creators})"
        if since is not None:
            query += f" AND dt.modified>={since.isoformat()}"
        return query

    async def async_count(self, authority: str) -> int:
        """Return how many publications an authority has (used to validate its name)."""
        total, _ = await self._request(self._query([authority]), 1, 1)
        return total

    async def async_search(self, authorities: list[str], since: date) -> list[Bekendmaking]:
        """Return all publications of the authorities modified on or after a date."""
        query = self._query(authorities, since)
        items: list[Bekendmaking] = []
        start = 1
        while True:
            total, page = await self._request(query, start, SRU_PAGE_SIZE)
            items.extend(page)
            start += SRU_PAGE_SIZE
            if not page or start > total:
                return items
