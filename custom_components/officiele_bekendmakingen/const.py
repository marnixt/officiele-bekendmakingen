"""Constants for the Officiële Bekendmakingen integration."""

from datetime import timedelta

DOMAIN = "officiele_bekendmakingen"

SRU_URL = "https://repository.overheid.nl/sru"
# The SRU service refuses pages larger than this.
SRU_PAGE_SIZE = 1000

# PDOK Locatieserver, only used by the config flow to suggest authorities near a zone.
LOCATIESERVER_REVERSE_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"

CONF_ZONE = "zone"
CONF_AUTHORITIES = "authorities"
CONF_RADIUS = "radius"
CONF_DAYS = "days"

DEFAULT_ZONE = "zone.home"
DEFAULT_RADIUS = 1000  # metres around the zone
DEFAULT_DAYS = 14

SCAN_INTERVAL = timedelta(hours=1)

# Number of publications exposed in the sensor attributes.
MAX_ATTRIBUTE_ITEMS = 20
# Number of publications shown on the map as geo_location entities (closest first).
MAX_MAP_ITEMS = 50

# Fired once for every publication that newly appears within the radius.
EVENT_NEW_PUBLICATION = f"{DOMAIN}_new_publication"
# How long announced publications are remembered, so they are not announced again.
SEEN_RETENTION = timedelta(days=365)
STORAGE_VERSION = 1
