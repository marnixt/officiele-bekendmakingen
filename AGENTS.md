## Workspace Notes
- Home Assistant custom integration, domain `officiele_bekendmakingen`.
- The integration assumes a clean configuration and does not include migration logic for legacy entries.
- Keep user documentation generic (no local paths, no private server references).

## Data source
- Publications come only from the SRU search service at `https://repository.overheid.nl/sru` (SRU 2.0, CQL
  queries). Do not use the RSS feed or per-item metadata/XML downloads: SRU already returns everything needed.
- Query: `c.product-area==officielepublicaties AND (dt.creator=="<a>" OR dt.creator=="<b>") AND dt.modified>=<date>`.
- `maximumRecords` is at most 1000; larger values return a diagnostic instead of records. Page with `startRecord`.
- An unknown or misspelled authority returns 0 records.
- SRU's spatial indexes (`w.locatiepunt`, `cd.afgeleideLocatieGebied`, relation `within`) fail server-side
  ("Undefined simple type point"), so SRU cannot be searched by location.
- The config flow uses the PDOK Locatieserver reverse endpoint
  (`type=gemeente&type=provincie&type=waterschap&distance=<radius>`) to suggest authorities around a zone.
  Its `gemeentenaam`, `provincienaam` and `waterschapsnaam` match `dt.creator` exactly.
- Useful fields per record: `dcterms:type` (rubriek), `overheidwetgeving:activiteit`,
  `overheidwetgeving:datumEindeReactietermijn`, `overheidwetgeving:locatiegebied` (WGS84 WKT, "lon lat"),
  `gzd:preferredUrl`.

## Background
- This is a rebuild, not a fork, of the community integration DonTranQuiL/Bekendmakingen. Avoid its problems:
  RSS plus extra requests per item, a 50-item cap with filtering afterwards, no radius filter, only the
  Gemeenteblad with no check of the municipality name, errors swallowed so stale data shows as "OK",
  cache files written loose in `/config`, and categories guessed from keywords instead of read from rubriek.
- Worth keeping from it: a custom dashboard card and reading out the reaction period.

## Status and next steps
- 0.1.0 scaffold: SRU client, config flow (authority, radius, days), coordinator that filters by distance
  to the HA home location, sensors "nearby" (count + items) and "next_reaction_deadline".
- Repository: https://github.com/marnixt/officiele-bekendmakingen.
- 0.2.0: `geo_location` entities (one per nearby publication, capped at `MAX_MAP_ITEMS`); entities that
  drop out are removed from the entity registry.
- 0.3.0: config entry per zone (unique id = zone entity id) with a list of authorities picked in a second
  step; event `officiele_bekendmakingen_new_publication`, with announced ids kept in a `Store` (nothing is
  announced on the first run).
- Next: filters on rubriek/activiteit, an options flow to change authorities/radius/days.

## Conventions
- Errors from the service raise `UpdateFailed`; never return stale data silently.
- Persistent data goes through `homeassistant.helpers.storage.Store`, never loose files in `/config`.
- Run `ruff check custom_components tests` and `python -m pytest` before committing.
- Deploy to a test HA with `scripts/deploy.ps1` (only committed code is deployed).
