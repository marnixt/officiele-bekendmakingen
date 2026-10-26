"""Tests for the nearest-location helper and the map entities."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from custom_components.officiele_bekendmakingen.api import Bekendmaking
from custom_components.officiele_bekendmakingen.const import DOMAIN
from custom_components.officiele_bekendmakingen.coordinator import (
    NearbyBekendmaking,
    nearest_location,
)
from custom_components.officiele_bekendmakingen.geo_location import PublicationEvent

HOME = (51.56, 5.09)

ITEM = Bekendmaking(
    identifier="gmb-2026-1",
    title="Besluit omgevingsvergunning, Voorbeeldstraat 1",
    authority="Voorbeeldstad",
    rubriek="omgevingsvergunning",
    activiteit="kappen",
    published=date(2026, 10, 23),
    reaction_deadline=date(2026, 12, 2),
    url="https://zoek.officielebekendmakingen.nl/gmb-2026-1.html",
    locations=((51.60, 5.09), (51.57, 5.09)),
)


def test_nearest_location_picks_closest_area():
    dist, location = nearest_location(HOME, ITEM.locations)
    assert location == (51.57, 5.09)
    # 0.01 degree of latitude is about 1.1 km.
    assert dist == pytest.approx(1112, rel=0.01)


def test_nearest_location_without_locations():
    assert nearest_location(HOME, ()) is None


def test_publication_event():
    nearby = NearbyBekendmaking(ITEM, 1234.4, (51.57, 5.09))
    entity = PublicationEvent(MagicMock(), "entry_gmb-2026-1", nearby)

    assert entity.unique_id == "entry_gmb-2026-1"
    assert entity.name == ITEM.title
    assert entity.source == DOMAIN
    assert (entity.latitude, entity.longitude) == (51.57, 5.09)
    assert entity.distance == pytest.approx(1.2344)
    assert entity.extra_state_attributes == {
        "title": ITEM.title,
        "rubriek": "omgevingsvergunning",
        "activiteit": "kappen",
        "authority": "Voorbeeldstad",
        "published": "2026-10-23",
        "reaction_deadline": "2026-12-02",
        "distance_m": 1234,
        "url": ITEM.url,
    }
