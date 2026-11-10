# Officiële Bekendmakingen for Home Assistant

Follow official government publications (permits, events, traffic decisions, tree felling, …)
near your home, using the public SRU search service of
[officielebekendmakingen.nl](https://www.officielebekendmakingen.nl).

*Nederlands: zie [README.nl.md](https://github.com/marnixt/officiele-bekendmakingen/blob/main/README.nl.md).*

> Status: early development (0.5.0).

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
  background maps from PDOK (Kadaster). New publications get a *New* badge until you open them.
- **Follow an address**: mark the address of a publication, and that publication and every
  later one at the same address get a *Followed* badge and `followed: true`.
- **AI summaries** (optional): pick an [AI task](https://www.home-assistant.io/integrations/ai_task/)
  entity in the options and every publication within the radius gets a short summary and an
  impact rating (low/medium/high).
- **Event** `officiele_bekendmakingen_new_publication` for every publication that newly appears
  within the radius, including its summary when summaries are on. Publications already present
  when the integration is first set up are not announced.
- **Options**: change the radius, look-back period, authorities, AI task entity and summary
  language afterwards
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
list_sort: distance      # distance, first_seen, reaction_deadline or published
list_height: 400         # height of the list in px (it scrolls); 0 = no limit
open_only: false         # only publications whose reaction period is still open
tap_action: details      # details (next to the list), popup or more-info
attributes:              # fields in the details, in this order
  - summary
  - impact
  - abstract
  - address
  - rubriek
  - activiteit
  - authority
  - published
  - first_seen
  - reaction_deadline
  - distance_m
labels:                  # optional: own names for the fields
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
The details have buttons to the publication, the standard details dialog, *Follow address* and
*Hide*.

### The list and details
With `show_list: true` the card shows a list below the map with the details of the selected
publication next to it (above it on a narrow card, such as on a phone). Clicking a marker
selects that publication: it is highlighted on the map and in the list, the list scrolls to it
and its details are shown. Clicking a row does the same and moves the map to it. Without a list,
or with `tap_action: popup`, a marker opens a popup with the details instead.

Each row shows the address (when
the publication has one), the distance and when the integration fetched it ("fetched 3 hours
ago"), plus badges:

- **New**: fetched since you last looked. The badge disappears once you open the publication;
  *Mark all read* clears all of them. The first time you use the card, the publications already
  there count as read.
- **Followed**: about an address you follow. Followed publications are always at the top of the
  list and have a yellow ring on the map.
- **Days left** to react, orange when 6 days or fewer are left and red at 2 days or fewer.

Above the list you can sort by *Distance*, *Newest first* (most recently fetched first) or
*Deadline* (open reaction periods first, soonest first), and filter on *New*, *Followed* and
*Open for reactions*. Filters apply to the map as well. Hidden publications only show up with
the *Hidden* filter, where you can show them again.

What you have viewed or hidden is stored per Home Assistant user, so it is the same on all your
devices. The chosen sort order and filters are remembered per browser.

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
is tried again an hour later. After a restart the integration waits up to five minutes for the
AI task entity to appear.

With a cloud AI service, each summary is one paid request. As an indication: 100 summaries cost
about 1 cent with gpt-6-luna.

## Following an address
Use *Follow address* in the details on the map card, or the actions
`officiele_bekendmakingen.follow` and `officiele_bekendmakingen.unfollow` with the `identifier`
of a publication within the radius:

```yaml
action: officiele_bekendmakingen.follow
data:
  identifier: gmb-2026-123456
```

A later publication is about the same address when both have the same postcode and house
number. When either has no address (many publications only mark an area), it counts when one
of its locations lies within 25 m of the followed one. Unfollowing a publication stops following
its address. Followed addresses are stored per zone.

## Notification on new publications
The event data contains `title`, `address`, `rubriek`, `activiteit`, `abstract`, `authority`,
`published`, `first_seen`, `reaction_deadline`, `distance_m`, `url`, `summary`, `impact`,
`followed`, `identifier`, `zone` and `entry_id`. `summary` and `impact` are empty when AI
summaries are off.

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

Only for followed addresses: add a condition.

```yaml
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.followed }}"
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
