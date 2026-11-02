# Officiële Bekendmakingen for Home Assistant

Follow official government publications (permits, events, traffic decisions, tree felling, …)
near your home, using the public SRU search service of
[officielebekendmakingen.nl](https://www.officielebekendmakingen.nl).

> Status: early development (0.4.0).

## Features
- Choose a zone (home or any other zone), a radius around it and how many days to look back.
  The integration then lists the municipalities, provinces and water boards whose area lies
  within the radius (looked up with the [PDOK Locatieserver](https://www.pdok.nl)) so you can
  pick which ones to follow. The ones the zone itself lies in are preselected.
- **Nearby publications** sensor: the number of publications within the radius, with the closest
  ones (title, rubriek, activity, distance, link) as attributes.
- **Next reaction deadline** sensor: the first upcoming end of a reaction or objection period.
- **Map**: every publication within the radius (up to 50, closest first) is a `geo_location`
  entity at the centre of its marked area, with an icon per rubriek (and activity, e.g. a tree
  for felling). Entities appear and disappear as publications come and go.
- **Map card** `custom:bekendmakingen-map-card`, loaded automatically: coloured markers per
  rubriek, a popup with the fields you choose, an optional list below the map and Dutch
  background maps from PDOK (Kadaster).
- **AI summaries** (optional): pick an [AI task](https://www.home-assistant.io/integrations/ai_task/)
  entity in the options and every publication within the radius gets a short summary and an
  impact rating (low/medium/high).
- **Event** `officiele_bekendmakingen_new_publication` for every publication that newly appears
  within the radius, including its summary when summaries are on. Publications already present
  when the integration is first set up are not announced.
- **Options**: change the radius, look-back period, authorities and AI task entity afterwards
  under *Settings → Devices & services → Officiële Bekendmakingen → Configure*.

## Map card
The integration ships its own map card. Add it from the card picker (*Bekendmakingen kaart*)
and configure it in the UI, or in YAML:

```yaml
type: custom:bekendmakingen-map-card
title: Bekendmakingen
zone: zone.home          # only publications of this zone; omit to show all zones
radius: 1000             # draw the search radius around the zone (metres)
height: 400
tiles: pdok              # pdok, pdok_grijs, pdok_luchtfoto, osm or a {z}/{x}/{y} URL template
dark_mode: auto          # auto, light or dark
show_list: true          # list below the map
list_sort: distance      # distance, reaction_deadline or published
open_only: false         # only publications whose reaction period is still open
tap_action: popup        # popup or more-info
attributes:              # popup fields, in this order
  - summary
  - impact
  - abstract
  - rubriek
  - activiteit
  - authority
  - published
  - reaction_deadline
  - distance_m
labels:                  # optional: own names for popup fields
  reaction_deadline: Zienswijze tot
include_rubrieken: []    # only these rubrieken
exclude_rubrieken:
  - verkiezingen
styles:                  # optional: colour and icon per rubriek or activity
  evenementenvergunning:
    color: "#9c27b0"
  kappen:
    icon: mdi:pine-tree
```

Every attribute of a publication entity can be used under `attributes`; dates, distance and
the impact rating are formatted, the reaction deadline shows the number of days left.
The popup has a button to the publication and one to the standard details dialog.

The standard map card also works, but shows the first letters of each title on the markers:

```yaml
type: map
geo_location_sources:
  - officiele_bekendmakingen
```

## AI summaries
1. Set up an AI integration that provides an AI task entity (for example OpenAI, Google
   Gemini, Anthropic or Ollama).
2. Open the options of a zone and choose that entity under *AI task for summaries*.
3. Optionally pick another *Summary language*; the default is Dutch, the language of the
   publications. Summaries in another language are rewritten after a change.

The integration then fetches the text of each publication within the radius once and asks
the AI task for a summary and an impact rating. Summaries are stored, so a publication is
never summarised twice. New publications are summarised before they are announced; older ones
are caught up ten per hour, closest first. A failed summary only leaves the summary empty and
is tried again an hour later. With a cloud AI service, each summary is one paid request.

## Notification on new publications
The event data contains `title`, `rubriek`, `activiteit`, `abstract`, `authority`, `published`,
`reaction_deadline`, `distance_m`, `url`, `summary`, `impact`, `identifier`, `zone` and
`entry_id`. `summary` and `impact` are empty when AI summaries are off.

```yaml
triggers:
  - trigger: event
    event_type: officiele_bekendmakingen_new_publication
actions:
  - action: notify.notify
    data:
      title: "New publication ({{ trigger.event.data.distance_m }} m)"
      message: "{{ trigger.event.data.summary or trigger.event.data.title }}"
      data:
        url: "{{ trigger.event.data.url }}"
```

## Installation
1. Add this repository as a custom repository in HACS (category: Integration).
2. Install **Officiële Bekendmakingen** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and search for *Officiële Bekendmakingen*.

## Development
```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # Windows: .venv\Scripts\pip
ruff check custom_components tests
python -m pytest
```
