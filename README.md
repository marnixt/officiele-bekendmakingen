# Officiële Bekendmakingen for Home Assistant

Follow official government publications (permits, events, traffic decisions, tree felling, …)
near your home, using the public SRU search service of
[officielebekendmakingen.nl](https://www.officielebekendmakingen.nl).

> Status: early development (0.3.0).

## Features
- Choose a zone (home or any other zone), a radius around it and how many days to look back.
  The integration then lists the municipalities, provinces and water boards whose area lies
  within the radius (looked up with the [PDOK Locatieserver](https://www.pdok.nl)) so you can
  pick which ones to follow. The ones the zone itself lies in are preselected.
- **Nearby publications** sensor: the number of publications within the radius, with the closest
  ones (title, rubriek, activity, distance, link) as attributes.
- **Next reaction deadline** sensor: the first upcoming end of a reaction or objection period.
- **Map**: every publication within the radius (up to 50, closest first) is a `geo_location`
  entity at the centre of its marked area. Entities appear and disappear as publications come
  and go.
- **Event** `officiele_bekendmakingen_new_publication` for every publication that newly appears
  within the radius. Publications already present when the integration is first set up are not
  announced.

## Map card
```yaml
type: map
geo_location_sources:
  - officiele_bekendmakingen
```

## Notification on new publications
The event data contains `title`, `rubriek`, `activiteit`, `authority`, `published`,
`reaction_deadline`, `distance_m`, `url`, `identifier`, `zone` and `entry_id`.

```yaml
triggers:
  - trigger: event
    event_type: officiele_bekendmakingen_new_publication
actions:
  - action: notify.notify
    data:
      title: "New publication ({{ trigger.event.data.distance_m }} m)"
      message: "{{ trigger.event.data.title }}"
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
