"""Tests for followed addresses."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.officiele_bekendmakingen.api import Address, Bekendmaking
from custom_components.officiele_bekendmakingen.coordinator import (
    BekendmakingenCoordinator,
    NearbyBekendmaking,
)
from custom_components.officiele_bekendmakingen.follow import Follow, follow_for, matches

# 0.0001 degree of latitude is about 11 m.
POINT = (51.5700, 5.0900)


def _nearby(
    identifier: str = "gmb-1",
    locations: tuple[tuple[float, float], ...] = (POINT,),
    addresses: tuple[Address, ...] = (),
) -> NearbyBekendmaking:
    item = Bekendmaking(
        identifier,
        f"Aanvraag omgevingsvergunning {identifier}",
        None,
        None,
        None,
        None,
        None,
        None,
        locations=locations,
        addresses=addresses,
    )
    return NearbyBekendmaking(item, 100.0, locations[0])


HOUSE = Address("Voorbeeldstraat", "12", "1234AB", "Voorbeeldstad")
NEIGHBOUR = Address("Voorbeeldstraat", "14", "1234AB", "Voorbeeldstad")


def test_follow_for_publication_with_address():
    follow = follow_for(_nearby(addresses=(HOUSE,)))
    assert follow == Follow("Voorbeeldstraat 12, Voorbeeldstad", *POINT, "1234AB", "12")


def test_follow_for_publication_without_address_uses_title():
    follow = follow_for(_nearby())
    assert follow == Follow("Aanvraag omgevingsvergunning gmb-1", *POINT)


def test_follow_round_trips_through_storage():
    follow = Follow("Voorbeeldstraat 12, Voorbeeldstad", *POINT, "1234AB", "12")
    assert Follow.from_dict(follow.as_dict()) == follow


def test_matches_same_address_far_away():
    follow = follow_for(_nearby(addresses=(HOUSE,)))
    # The same address, but marked at the other end of a large plot.
    assert matches(follow, _nearby("gmb-2", ((51.5710, 5.0900),), (HOUSE,)))


def test_neighbour_does_not_match_although_close():
    follow = follow_for(_nearby(addresses=(HOUSE,)))
    assert not matches(follow, _nearby("gmb-2", ((51.5701, 5.0900),), (NEIGHBOUR,)))


def test_matches_by_distance_without_address():
    follow = follow_for(_nearby(addresses=(HOUSE,)))
    assert matches(follow, _nearby("gmb-2", ((51.5702, 5.0900),)))
    assert not matches(follow, _nearby("gmb-3", ((51.5704, 5.0900),)))


def test_matches_any_location_of_a_publication():
    follow = follow_for(_nearby())
    assert matches(follow, _nearby("gmb-2", ((51.6, 5.1), (51.5701, 5.0900))))


@pytest.mark.asyncio
async def test_coordinator_follow_and_unfollow():
    first = _nearby("gmb-1", addresses=(HOUSE,))
    later = _nearby("gmb-2", ((51.5710, 5.0900),), (HOUSE,))
    other = _nearby("gmb-3", ((51.5701, 5.0900),), (NEIGHBOUR,))
    coordinator = BekendmakingenCoordinator.__new__(BekendmakingenCoordinator)
    coordinator.data = [first, later, other]
    coordinator._seen = {"gmb-2": "2026-10-26T14:30:05+01:00"}
    coordinator._summaries = {}
    coordinator._follows = []
    coordinator._follow_store = AsyncMock()
    coordinator.async_update_listeners = MagicMock()

    await coordinator.async_follow("gmb-1")
    await coordinator.async_follow("gmb-2")  # same address: nothing new to follow

    assert coordinator._follows == [follow_for(first)]
    coordinator._follow_store.async_save.assert_awaited_once_with([follow_for(first).as_dict()])
    attributes = coordinator.attributes(later)
    assert attributes["followed"] is True
    assert attributes["first_seen"] == "2026-10-26T14:30:05+01:00"
    assert coordinator.attributes(other)["followed"] is False

    # Unfollowing from a later publication stops following the address.
    await coordinator.async_unfollow("gmb-2")
    assert coordinator._follows == []
    assert coordinator.async_update_listeners.call_count == 2
