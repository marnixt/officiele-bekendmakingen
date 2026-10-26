"""Constants for the Officiële Bekendmakingen integration."""

from datetime import timedelta

DOMAIN = "officiele_bekendmakingen"

SRU_URL = "https://repository.overheid.nl/sru"
# The SRU service refuses pages larger than this.
SRU_PAGE_SIZE = 1000

CONF_AUTHORITY = "authority"
CONF_RADIUS = "radius"
CONF_DAYS = "days"

DEFAULT_RADIUS = 1000  # metres around the home zone
DEFAULT_DAYS = 14

SCAN_INTERVAL = timedelta(hours=1)

# Number of publications exposed in the sensor attributes.
MAX_ATTRIBUTE_ITEMS = 20
# Number of publications shown on the map as geo_location entities (closest first).
MAX_MAP_ITEMS = 50
