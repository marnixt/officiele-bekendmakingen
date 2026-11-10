"""Followed addresses: publications at such an address are marked as followed."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.util.location import distance

from .const import FOLLOW_DISTANCE

if TYPE_CHECKING:
    from .coordinator import NearbyBekendmaking


@dataclass(frozen=True)
class Follow:
    """An address to follow, taken from a publication the user picked."""

    label: str
    latitude: float
    longitude: float
    # Normalised postcode and house number, when the publication had an address.
    postcode: str | None = None
    number: str | None = None

    @property
    def key(self) -> tuple[str, str] | None:
        return (self.postcode, self.number) if self.postcode and self.number else None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Follow:
        return cls(
            label=data["label"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            postcode=data.get("postcode"),
            number=data.get("number"),
        )


def follow_for(nearby: NearbyBekendmaking) -> Follow:
    """Return the address to follow for a publication."""
    item = nearby.item
    address = next((a for a in item.addresses if a.key), None)
    key = address.key if address else None
    return Follow(
        label=item.address or item.title,
        latitude=nearby.location[0],
        longitude=nearby.location[1],
        postcode=key[0] if key else None,
        number=key[1] if key else None,
    )


def matches(follow: Follow, nearby: NearbyBekendmaking) -> bool:
    """Return whether a publication is about a followed address.

    When both have a postcode and house number, those decide: neighbours are often closer
    than FOLLOW_DISTANCE. Otherwise any marked location within FOLLOW_DISTANCE counts.
    """
    keys = {a.key for a in nearby.item.addresses if a.key}
    if follow.key and keys:
        return follow.key in keys
    return any(
        (d := distance(follow.latitude, follow.longitude, lat, lon)) is not None
        and d <= FOLLOW_DISTANCE
        for lat, lon in nearby.item.locations
    )
