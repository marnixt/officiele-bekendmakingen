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
CONF_AI_TASK_ENTITY = "ai_task_entity"
CONF_SUMMARY_LANGUAGE = "summary_language"

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

# Followed addresses: a publication without a matching postcode and house number is about
# a followed address when one of its locations lies within this distance of it.
FOLLOW_DISTANCE = 25  # metres
SERVICE_FOLLOW = "follow"
SERVICE_UNFOLLOW = "unfollow"
ATTR_IDENTIFIER = "identifier"

# AI summaries: generated with ai_task.generate_data from the publication text.
# Older publications without a summary are caught up a few at a time, closest first.
MAX_SUMMARIES_PER_UPDATE = 10
# Publication texts are short; longer ones are cut off before they are sent to the AI.
MAX_SUMMARY_INPUT_CHARS = 20000
IMPACT_LEVELS = ["low", "medium", "high"]
# After a restart the AI task entity may be set up after this integration; wait for it.
AI_WAIT_INTERVAL = 30  # seconds
AI_WAIT_ATTEMPTS = 10
# Publications are in Dutch, so summaries are too unless another language is chosen.
DEFAULT_SUMMARY_LANGUAGE = "nl"

# Map card shipped with the integration.
FRONTEND_URL_PATH = f"/{DOMAIN}/frontend"
CARD_FILENAME = "bekendmakingen-map-card.js"

DEFAULT_ICON = "mdi:file-document-outline"
# Icon per rubriek (dcterms:type); an activity can refine it.
RUBRIEK_ICONS = {
    "omgevingsvergunning": "mdi:home-edit",
    "omgevingsmelding": "mdi:bullhorn",
    "andere vergunning": "mdi:file-certificate",
    "andere beschikking": "mdi:file-sign",
    "andere melding": "mdi:message-alert",
    "verkeersbesluit of -mededeling": "mdi:traffic-cone",
    "evenementenvergunning": "mdi:party-popper",
    "exploitatievergunning": "mdi:store",
    "vergunning voor activiteiten op of in oppervlaktewater": "mdi:waves",
    "algemeen verbindend voorschrift (verordening)": "mdi:gavel",
    "ander besluit van algemene strekking": "mdi:gavel",
    "ruimtelijk plan of omgevingsdocument": "mdi:map-legend",
    "participatie": "mdi:account-group",
    "vergadering of stuk van het bestuur": "mdi:account-tie",
    "verkiezingen": "mdi:vote",
}
ACTIVITEIT_ICONS = {
    "kappen": "mdi:tree",
    "slopen": "mdi:excavator",
    "reclame": "mdi:billboard",
    "milieu": "mdi:factory",
}
