"""Tests for the publication text, AI responses and which publications get a summary."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.officiele_bekendmakingen.api import Bekendmaking
from custom_components.officiele_bekendmakingen.const import (
    EVENT_NEW_PUBLICATION,
    MAX_SUMMARIES_PER_UPDATE,
)
from custom_components.officiele_bekendmakingen.coordinator import (
    BekendmakingenCoordinator,
    NearbyBekendmaking,
    publication_icon,
    summary_backlog,
)
from custom_components.officiele_bekendmakingen.summary import (
    SummaryError,
    extract_text,
    parse_result,
)

COORDINATOR = "custom_components.officiele_bekendmakingen.coordinator"

# Trimmed publication XML from repository.overheid.nl.
PUBLICATION = """<officiele-publicatie><metadata><meta name="x" content="y" /></metadata>
<kop><titel>GEMEENTEBLAD</titel></kop>
<gemeenteblad><kop><titel>Aanvraag omgevingsvergunning, Voorbeeldstraat 1</titel></kop>
<zakelijke-mededeling><zakelijke-mededeling-tekst><tekst>
<al>De aanvraag gaat over:</al>
<al>Omschrijving: <nadruk type="vet">vervangen   van de dakkapel</nadruk></al>
<lijst><li><li.nr>•</li.nr><al>Bouwactiviteit</al></li></lijst>
</tekst></zakelijke-mededeling-tekst></zakelijke-mededeling></gemeenteblad></officiele-publicatie>
"""


def _item(identifier: str = "gmb-1", **kwargs) -> Bekendmaking:
    return Bekendmaking(identifier, identifier, None, None, None, None, None, None, **kwargs)


def test_extract_text_one_paragraph_per_line():
    assert extract_text(PUBLICATION) == (
        "GEMEENTEBLAD\n"
        "Aanvraag omgevingsvergunning, Voorbeeldstraat 1\n"
        "De aanvraag gaat over:\n"
        "Omschrijving: vervangen van de dakkapel\n"
        "Bouwactiviteit"
    )


def test_extract_text_invalid_xml_raises():
    with pytest.raises(SummaryError):
        extract_text("<html><body>not closed")


def test_parse_result():
    response = {"conversation_id": "x", "data": {"summary": " Kort. ", "impact": "medium"}}
    assert parse_result(response) == {"summary": "Kort.", "impact": "medium"}


def test_parse_result_drops_unknown_impact():
    assert parse_result({"data": {"summary": "Kort.", "impact": "enorm"}}) == {"summary": "Kort."}


@pytest.mark.parametrize("response", [None, {"data": "tekst"}, {"data": {"impact": "low"}}])
def test_parse_result_unexpected_raises(response):
    with pytest.raises(SummaryError):
        parse_result(response)


def test_summary_backlog_skips_summarised_and_is_capped():
    nearby = [NearbyBekendmaking(_item(f"gmb-{i}"), i, (51.5, 5.0)) for i in range(30)]
    backlog = summary_backlog(nearby, {"gmb-0": {"summary": "x", "language": "nl"}}, "nl")
    assert [n.item.identifier for n in backlog] == [
        f"gmb-{i}" for i in range(1, MAX_SUMMARIES_PER_UPDATE + 1)
    ]


def test_summary_in_another_language_is_redone():
    summaries = {
        "gmb-nl": {"summary": "Kort.", "language": "nl"},
        "gmb-en": {"summary": "Short.", "language": "en"},
        "gmb-old": {"summary": "Short."},
    }
    nearby = [NearbyBekendmaking(_item(i), 1.0, (51.5, 5.0)) for i in summaries]
    assert [n.item.identifier for n in summary_backlog(nearby, summaries, "nl")] == [
        "gmb-en",
        "gmb-old",
    ]


def test_publication_icon():
    assert publication_icon(_item()) == "mdi:file-document-outline"
    tree = Bekendmaking("x", "x", None, "omgevingsvergunning", "kappen", date(2026, 1, 1), None, None)
    assert publication_icon(tree) == "mdi:tree"
    event = Bekendmaking("x", "x", None, "evenementenvergunning", None, None, None, None)
    assert publication_icon(event) == "mdi:party-popper"


def _coordinator(options: dict, summaries: dict, pending: list, latest: list):
    """A coordinator with just enough state to run the summary worker."""
    coordinator = BekendmakingenCoordinator.__new__(BekendmakingenCoordinator)
    coordinator.hass = MagicMock()
    coordinator.config_entry = MagicMock(
        options=options, data={"zone": "zone.home"}, entry_id="entry"
    )
    coordinator._session = None
    coordinator._summaries = summaries
    coordinator._summary_store = AsyncMock()
    coordinator._pending = pending
    coordinator._latest = latest
    coordinator.async_update_listeners = MagicMock()
    return coordinator


@pytest.mark.asyncio
async def test_worker_summarises_before_announcing_and_forgets_old_summaries():
    new, older = (NearbyBekendmaking(_item(i), 10.0, (51.5, 5.0)) for i in ("gmb-new", "gmb-old"))
    coordinator = _coordinator(
        {"ai_task_entity": "ai_task.test", "summary_language": "nl"},
        {"gmb-gone": {"summary": "weg"}},
        [new],
        [new, older],
    )
    summarize = AsyncMock(
        side_effect=lambda hass, entity, item, text, language: {
            "summary": item.identifier,
            "language": language,
        }
    )
    with (
        patch(f"{COORDINATOR}.async_fetch_text", AsyncMock(return_value="tekst")),
        patch(f"{COORDINATOR}.async_summarize", summarize),
    ):
        await coordinator._async_work()

    event, data = coordinator.hass.bus.async_fire.call_args.args
    assert event == EVENT_NEW_PUBLICATION
    assert data["identifier"] == "gmb-new"
    assert data["summary"] == "gmb-new"
    assert coordinator._summaries == {
        "gmb-new": {"summary": "gmb-new", "language": "nl"},
        "gmb-old": {"summary": "gmb-old", "language": "nl"},
    }
    coordinator._summary_store.async_save.assert_awaited_once_with(coordinator._summaries)
    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_worker_announces_without_ai_and_survives_failures():
    new = NearbyBekendmaking(_item("gmb-new"), 10.0, (51.5, 5.0))
    coordinator = _coordinator({}, {}, [new], [new])
    await coordinator._async_work()
    assert coordinator.hass.bus.async_fire.call_args.args[1]["summary"] is None
    coordinator._summary_store.async_save.assert_not_awaited()

    coordinator = _coordinator({"ai_task_entity": "ai_task.test"}, {}, [new], [new])
    with patch(f"{COORDINATOR}.async_fetch_text", AsyncMock(side_effect=SummaryError("down"))):
        await coordinator._async_work()
    assert coordinator.hass.bus.async_fire.call_count == 1
    assert coordinator._summaries == {}
