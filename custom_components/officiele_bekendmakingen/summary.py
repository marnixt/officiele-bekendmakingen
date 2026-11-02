"""AI summaries of publications, generated with the ai_task integration."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api import Bekendmaking
from .const import IMPACT_LEVELS, MAX_SUMMARY_INPUT_CHARS

_TIMEOUT = aiohttp.ClientTimeout(total=30)
_AI_TIMEOUT = 120  # seconds
# Elements that hold a paragraph or heading of the publication text.
_BLOCKS = {"al", "titel", "tussenkop"}

INSTRUCTIONS = """\
Below is an official publication by a Dutch government authority.
Summarise it in two or three short sentences for someone living nearby: what is going to
happen, where, and what they can do about it (for example submit a view or an objection,
and until when). Leave out case numbers, phone numbers and standard legal text.
Also rate the impact for people living right next to the location: low, medium or high.
Write the summary in the language with code "{language}".

Title: {title}
Category: {rubriek}
Authority: {authority}

Text:
{text}
"""

STRUCTURE = {
    "summary": {
        "description": "Summary of two or three sentences.",
        "required": True,
        "selector": {"text": {"multiline": True}},
    },
    "impact": {
        "description": "Impact for people living right next to the location.",
        "required": True,
        "selector": {"select": {"options": IMPACT_LEVELS}},
    },
}


class SummaryError(Exception):
    """Raised when a publication cannot be summarised."""


def extract_text(xml: str) -> str:
    """Return the readable text of a publication XML, one paragraph per line."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as err:
        raise SummaryError(f"Invalid publication XML: {err}") from err
    lines = []
    for element in root.iter():
        if element.tag in _BLOCKS:
            line = " ".join("".join(element.itertext()).split())
            if line:
                lines.append(line)
    return "\n".join(lines) or " ".join("".join(root.itertext()).split())


async def async_fetch_text(session: aiohttp.ClientSession, item: Bekendmaking) -> str:
    """Return the text of a publication, or its title and abstract when it has no text."""
    if item.content_url is None:
        return "\n".join(filter(None, [item.title, item.abstract]))
    try:
        async with session.get(item.content_url, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            body = await resp.text()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise SummaryError(f"Cannot fetch {item.content_url}: {err}") from err
    return extract_text(body)


def parse_result(response: Any) -> dict[str, str]:
    """Return the summary and impact from an ai_task.generate_data response."""
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
        raise SummaryError(f"Unexpected AI response: {response!r}")
    result = {"summary": data["summary"].strip()}
    if data.get("impact") in IMPACT_LEVELS:
        result["impact"] = data["impact"]
    return result


async def async_summarize(
    hass: HomeAssistant, entity_id: str, item: Bekendmaking, text: str
) -> dict[str, str]:
    """Ask the AI task entity for a summary and impact rating of a publication."""
    instructions = INSTRUCTIONS.format(
        language=hass.config.language,
        title=item.title,
        rubriek=item.rubriek or "-",
        authority=item.authority or "-",
        text=text[:MAX_SUMMARY_INPUT_CHARS],
    )
    try:
        async with asyncio.timeout(_AI_TIMEOUT):
            response = await hass.services.async_call(
                "ai_task",
                "generate_data",
                {
                    "task_name": f"Summarise {item.identifier}",
                    "entity_id": entity_id,
                    "instructions": instructions,
                    "structure": STRUCTURE,
                },
                blocking=True,
                return_response=True,
            )
    except (HomeAssistantError, vol.Invalid, TimeoutError) as err:
        raise SummaryError(f"AI task {entity_id} failed: {err}") from err
    return parse_result(response)
