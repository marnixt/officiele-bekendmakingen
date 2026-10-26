# Officiële Bekendmakingen for Home Assistant

Follow official government publications (permits, events, traffic decisions, tree felling, …)
near your home, using the public SRU search service of
[officielebekendmakingen.nl](https://www.officielebekendmakingen.nl).

> Status: early development (0.2.0).

## Features
- Configure a publishing authority (for example your municipality), a radius around the home
  zone and how many days to look back.
- **Nearby publications** sensor: the number of publications within the radius, with the closest
  ones (title, rubriek, activity, distance, link) as attributes.
- **Next reaction deadline** sensor: the first upcoming end of a reaction or objection period.
- **Map**: every publication within the radius (up to 50, closest first) is a `geo_location`
  entity at the centre of its marked area. Entities appear and disappear as publications come
  and go.

## Map card
```yaml
type: map
geo_location_sources:
  - officiele_bekendmakingen
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
