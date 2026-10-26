"""Tests for authority suggestions, the SRU query and remembering announced publications."""

from datetime import date

from custom_components.officiele_bekendmakingen.api import Bekendmaking, SruClient
from custom_components.officiele_bekendmakingen.config_flow import authority_options
from custom_components.officiele_bekendmakingen.coordinator import (
    NearbyBekendmaking,
    update_seen,
)
from custom_components.officiele_bekendmakingen.locatieserver import Authority, parse_authorities

# Trimmed response documents of the PDOK Locatieserver reverse endpoint.
DOCS = [
    {"type": "provincie", "provincienaam": "Noord-Brabant", "weergavenaam": "Provincie Noord-Brabant", "afstand": 0.0},
    {"type": "gemeente", "gemeentenaam": "Tilburg", "weergavenaam": "Gemeente Tilburg", "afstand": 0.0},
    {"type": "waterschap", "waterschapsnaam": "Waterschap De Dommel", "weergavenaam": "Waterschap De Dommel", "afstand": 0.0},
    {"type": "waterschap", "waterschapsnaam": "Waterschap Brabantse Delta", "weergavenaam": "Waterschap Brabantse Delta", "afstand": 2511.56},
    {"type": "gemeente", "gemeentenaam": "Goirle", "weergavenaam": "Gemeente Goirle", "afstand": 3395.65},
    {"type": "adres", "weergavenaam": "Ignored 1, Tilburg", "afstand": 10.0},
]


def test_parse_authorities_sorted_by_distance():
    authorities = parse_authorities(DOCS)
    assert [a.name for a in authorities] == [
        "Tilburg",
        "Noord-Brabant",
        "Waterschap De Dommel",
        "Waterschap Brabantse Delta",
        "Goirle",
    ]
    assert authorities[0] == Authority("Tilburg", "Gemeente Tilburg", 0.0)


def test_authority_options_show_distance_outside_zone():
    options = authority_options(parse_authorities(DOCS))
    assert options[0] == {"value": "Tilburg", "label": "Gemeente Tilburg"}
    assert options[-1] == {"value": "Goirle", "label": "Gemeente Goirle (3.4 km)"}


def test_query_combines_authorities():
    query = SruClient._query(["Tilburg", "Waterschap De Dommel"], date(2026, 10, 1))
    assert query == (
        "c.product-area==officielepublicaties AND "
        '(dt.creator=="Tilburg" OR dt.creator=="Waterschap De Dommel") '
        "AND dt.modified>=2026-10-01"
    )


def _nearby(identifier: str) -> NearbyBekendmaking:
    item = Bekendmaking(identifier, identifier, None, None, None, None, None, None)
    return NearbyBekendmaking(item, 100.0, (51.5, 5.0))


def test_update_seen_reports_only_new_publications():
    seen = {"gmb-1": "2026-10-20"}
    new, updated = update_seen(seen, [_nearby("gmb-1"), _nearby("gmb-2")], date(2026, 10, 26))
    assert [n.item.identifier for n in new] == ["gmb-2"]
    assert updated == {"gmb-1": "2026-10-20", "gmb-2": "2026-10-26"}


def test_update_seen_forgets_old_entries():
    seen = {"gmb-old": "2025-01-01", "gmb-1": "2026-10-20"}
    new, updated = update_seen(seen, [], date(2026, 10, 26))
    assert new == []
    assert updated == {"gmb-1": "2026-10-20"}
