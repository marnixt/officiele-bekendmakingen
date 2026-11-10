/*
 * Map card for the Officiële Bekendmakingen integration.
 *
 * Shows the publications (geo_location entities with source "officiele_bekendmakingen")
 * with an icon and colour per rubriek, and a popup with the attributes chosen in the card
 * configuration. Plain custom element without a build step; Leaflet is shipped alongside.
 *
 * What a user has viewed or hidden is kept in Home Assistant's per-user frontend storage,
 * so it is the same on all their devices. Followed addresses are kept by the integration.
 */

const TAG = "bekendmakingen-map-card";
const SOURCE = "officiele_bekendmakingen";
const BASE = new URL(".", import.meta.url).href;
// Key of the per-user frontend storage: { viewed: {id: time}, hidden: {id: time}, read_before }.
const USER_DATA_KEY = "officiele_bekendmakingen";
// Viewed and hidden marks older than this are dropped; publications are long gone by then.
const USER_DATA_RETENTION_MS = 400 * 86400000;
// Sort order and filters of the list, remembered per browser.
const UI_STORAGE_KEY = "bekendmakingen-map-card.list";

const TILES = {
  pdok: {
    url: "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png",
    attribution: 'Kaartgegevens &copy; <a href="https://www.kadaster.nl" target="_blank">Kadaster</a>',
  },
  pdok_grijs: {
    url: "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/grijs/EPSG:3857/{z}/{x}/{y}.png",
    attribution: 'Kaartgegevens &copy; <a href="https://www.kadaster.nl" target="_blank">Kadaster</a>',
  },
  pdok_luchtfoto: {
    url: "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
    attribution: '&copy; <a href="https://www.beeldmateriaal.nl" target="_blank">Beeldmateriaal Nederland</a>',
    photo: true,
  },
  osm: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>',
  },
};

// Colour per rubriek or activity (an activity wins); the icon comes from the entity.
const DEFAULT_STYLES = {
  omgevingsvergunning: { color: "#3b6fd4" },
  omgevingsmelding: { color: "#7b5cd6" },
  "andere vergunning": { color: "#0f8b7d" },
  "andere beschikking": { color: "#5f7a8a" },
  "andere melding": { color: "#8a6d5f" },
  "verkeersbesluit of -mededeling": { color: "#e8710a" },
  evenementenvergunning: { color: "#d6336c" },
  exploitatievergunning: { color: "#a87b00" },
  "vergunning voor activiteiten op of in oppervlaktewater": { color: "#0288d1" },
  "ruimtelijk plan of omgevingsdocument": { color: "#558b2f" },
  "algemeen verbindend voorschrift (verordening)": { color: "#6d4c41" },
  "ander besluit van algemene strekking": { color: "#6d4c41" },
  participatie: { color: "#00897b" },
  kappen: { color: "#2e7d32" },
};
const DEFAULT_COLOR = "#607d8b";
const DEFAULT_ICON = "mdi:file-document-outline";

const ALL_ATTRIBUTES = [
  "summary",
  "impact",
  "abstract",
  "address",
  "rubriek",
  "activiteit",
  "authority",
  "published",
  "first_seen",
  "reaction_deadline",
  "distance_m",
  "url",
];

// Sort orders offered above the list; the card configuration may also choose "published".
const LIST_SORTS = ["distance", "first_seen", "reaction_deadline"];
const LIST_FILTERS = ["new", "followed", "open", "hidden"];
// A reaction deadline this many days away or closer is shown in orange, URGENT_DAYS in red.
const SOON_DAYS = 6;
const URGENT_DAYS = 2;

const DEFAULT_CONFIG = {
  height: 400,
  tiles: "pdok",
  dark_mode: "auto",
  attributes: ["summary", "abstract", "address", "rubriek", "activiteit", "authority", "published", "first_seen", "reaction_deadline", "distance_m"],
  labels: {},
  styles: {},
  include_rubrieken: [],
  exclude_rubrieken: [],
  open_only: false,
  show_list: false,
  list_sort: "distance",
  tap_action: "popup",
};

const STRINGS = {
  nl: {
    view: "Bekijk bekendmaking",
    details: "Details",
    none: "Geen bekendmakingen gevonden.",
    noneFiltered: "Geen bekendmakingen met dit filter.",
    today: "laatste dag",
    daysLeft: (n) => (n === 1 ? "nog 1 dag" : `nog ${n} dagen`),
    expired: "verlopen",
    recenter: "Alles tonen",
    error: "De kaart kon niet worden geladen.",
    new: "Nieuw",
    followed: "Wordt gevolgd",
    follow: "Adres volgen",
    unfollow: "Niet meer volgen",
    hide: "Verbergen",
    unhide: "Weer tonen",
    markAllRead: "Alles gelezen",
    newCount: (n) => `${n} nieuw`,
    fetched: (when) => `opgehaald ${when}`,
    failed: "Dat is niet gelukt:",
    sorts: { distance: "Afstand", first_seen: "Nieuwste eerst", reaction_deadline: "Termijn", published: "Gepubliceerd" },
    filters: { new: "Nieuw", followed: "Gevolgd", open: "Termijn open", hidden: "Verborgen" },
    attributes: {
      summary: "Samenvatting",
      impact: "Impact",
      abstract: "Omschrijving",
      address: "Adres",
      rubriek: "Rubriek",
      activiteit: "Activiteit",
      authority: "Bevoegd gezag",
      published: "Gepubliceerd",
      first_seen: "Opgehaald",
      reaction_deadline: "Reageren tot",
      distance_m: "Afstand",
      url: "Link",
    },
    form: {
      title: "Titel",
      zone: "Zone (alleen bekendmakingen van deze zone)",
      radius: "Straal tekenen (m)",
      height: "Hoogte",
      tiles: "Achtergrondkaart",
      dark_mode: "Donkere modus",
      attributes: "Velden in de popup",
      include_rubrieken: "Alleen deze rubrieken",
      exclude_rubrieken: "Deze rubrieken verbergen",
      open_only: "Alleen met open reactietermijn",
      show_list: "Lijst onder de kaart",
      list_sort: "Lijst sorteren op",
      tap_action: "Bij klikken op een marker",
    },
  },
  en: {
    view: "View publication",
    details: "Details",
    none: "No publications found.",
    noneFiltered: "No publications match this filter.",
    today: "last day",
    daysLeft: (n) => (n === 1 ? "1 day left" : `${n} days left`),
    expired: "closed",
    recenter: "Show all",
    error: "The map could not be loaded.",
    new: "New",
    followed: "Followed",
    follow: "Follow address",
    unfollow: "Stop following",
    hide: "Hide",
    unhide: "Show again",
    markAllRead: "Mark all read",
    newCount: (n) => `${n} new`,
    fetched: (when) => `fetched ${when}`,
    failed: "That did not work:",
    sorts: { distance: "Distance", first_seen: "Newest first", reaction_deadline: "Deadline", published: "Published" },
    filters: { new: "New", followed: "Followed", open: "Open for reactions", hidden: "Hidden" },
    attributes: {
      summary: "Summary",
      impact: "Impact",
      abstract: "Description",
      address: "Address",
      rubriek: "Category",
      activiteit: "Activity",
      authority: "Authority",
      published: "Published",
      first_seen: "Fetched",
      reaction_deadline: "React until",
      distance_m: "Distance",
      url: "Link",
    },
    form: {
      title: "Title",
      zone: "Zone (only publications of this zone)",
      radius: "Draw radius (m)",
      height: "Height",
      tiles: "Background map",
      dark_mode: "Dark mode",
      attributes: "Fields in the popup",
      include_rubrieken: "Only these categories",
      exclude_rubrieken: "Hide these categories",
      open_only: "Only with an open reaction period",
      show_list: "List below the map",
      list_sort: "Sort list by",
      tap_action: "When a marker is clicked",
    },
  },
};

function strings(language) {
  return (language || "").startsWith("nl") ? STRINGS.nl : STRINGS.en;
}

let leafletPromise;

/** Load the bundled Leaflet once, without taking over a window.L of another card. */
function loadLeaflet() {
  if (!leafletPromise) {
    leafletPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `${BASE}leaflet/leaflet.js`;
      script.onload = () => resolve(window.L.noConflict());
      script.onerror = () => reject(new Error("Leaflet could not be loaded"));
      document.head.appendChild(script);
    });
  }
  return leafletPromise;
}

/** Parse "YYYY-MM-DD" as a local date. */
function parseDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value || "");
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
}

/** Parse a timestamp, or a plain date as local midnight; return milliseconds or NaN. */
function parseTime(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return parseDate(value).getTime();
  return Date.parse(value || "");
}

function daysUntil(value) {
  const date = parseDate(value);
  if (!date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((date - today) / 86400000);
}

/** Whether a reaction deadline is today or later (not when there is none). */
function isOpen(deadline) {
  const days = daysUntil(deadline);
  return days !== null && days >= 0;
}

function el(tag, props = {}, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "style") element.style.cssText = value;
    else if (key.startsWith("on")) element.addEventListener(key.slice(2), value);
    else if (key in element) element[key] = value;
    else element.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined && child !== false) element.append(child);
  }
  return element;
}

function loadUiState() {
  try {
    const stored = JSON.parse(localStorage.getItem(UI_STORAGE_KEY) || "{}");
    return {
      sort: typeof stored.sort === "string" ? stored.sort : null,
      filters: new Set(Array.isArray(stored.filters) ? stored.filters.filter((f) => LIST_FILTERS.includes(f)) : []),
    };
  } catch {
    return { sort: null, filters: new Set() };
  }
}

function saveUiState(ui) {
  try {
    localStorage.setItem(UI_STORAGE_KEY, JSON.stringify({ sort: ui.sort, filters: [...ui.filters] }));
  } catch {
    // Storage may be unavailable (private window); the choice then lasts for this page only.
  }
}

const CSS = `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .map {
    width: 100%;
    position: relative;
    z-index: 0;
    background: var(--secondary-background-color);
  }
  .message { padding: 16px; color: var(--secondary-text-color); }
  .dark .leaflet-layer.themed {
    filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9);
  }
  .leaflet-container { font: inherit; }
  .leaflet-control-attribution {
    background: rgba(255, 255, 255, 0.7);
    font-size: 10px;
  }
  .dark .leaflet-control-attribution { background: rgba(0, 0, 0, 0.5); color: #ccc; }
  .dark .leaflet-control-attribution a { color: #9cf; }
  .leaflet-bar a, .leaflet-bar a:hover {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    border-color: var(--divider-color);
    display: flex;
    align-items: center;
    justify-content: center;
    --mdc-icon-size: 18px;
  }
  .pin {
    position: relative;
    width: 30px;
    height: 30px;
    box-sizing: border-box;
    border-radius: 50%;
    background: var(--pin-color);
    border: 2px solid #fff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    --mdc-icon-size: 17px;
    cursor: pointer;
  }
  .pin.followed { box-shadow: 0 0 0 3px var(--bm-followed-color), 0 1px 6px rgba(0, 0, 0, 0.5); }
  .pin .dot {
    position: absolute;
    top: -3px;
    right: -3px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--bm-new-color);
    border: 2px solid #fff;
  }
  .pin.zone { background: var(--primary-color); width: 26px; height: 26px; --mdc-icon-size: 15px; }
  .radius { stroke: var(--primary-color); fill: var(--primary-color); }
  .leaflet-popup-content-wrapper, .leaflet-popup-tip {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
  }
  .leaflet-popup-content-wrapper { border-radius: 12px; }
  .leaflet-popup-content { margin: 12px 14px; line-height: 1.4; font-size: 14px; }
  .leaflet-container a.leaflet-popup-close-button { color: var(--secondary-text-color); }
  .popup .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--pin-color);
    --mdc-icon-size: 16px;
    padding-right: 16px;
  }
  .popup h3 { margin: 4px 0 8px; font-size: 15px; line-height: 1.3; font-weight: 600; }
  .popup .badges { margin: -2px 0 8px; }
  .popup dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 10px;
    margin: 0;
    font-size: 13px;
  }
  .popup dt { color: var(--secondary-text-color); }
  .popup dd { margin: 0; overflow-wrap: anywhere; }
  .popup .block { grid-column: 1 / -1; }
  .popup dd.block { margin-bottom: 6px; }
  .popup .impact {
    display: inline-block;
    padding: 0 6px;
    border-radius: 8px;
    font-size: 12px;
    color: #fff;
  }
  .impact.low { background: #2e7d32; }
  .impact.medium { background: #e8710a; }
  .impact.high { background: #c62828; }
  .popup .actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .popup .actions a, .popup .actions button {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 14px;
    cursor: pointer;
    text-decoration: none;
    --mdc-icon-size: 16px;
  }
  .popup .actions a { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .popup .actions button {
    background: none;
    border: 1px solid var(--divider-color);
    color: var(--primary-text-color);
  }
  .popup .actions button.on { border-color: var(--bm-followed-color); }
  .badges { display: flex; flex-wrap: wrap; gap: 4px; }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-size: 11px;
    font-weight: 600;
    line-height: 16px;
    padding: 1px 7px;
    border-radius: 9px;
    white-space: nowrap;
    --mdc-icon-size: 13px;
  }
  .badge.new { background: var(--bm-new-color); color: #fff; }
  .badge.followed { background: var(--bm-followed-color); color: #3a2a00; }
  .badge.deadline { background: var(--secondary-background-color); color: var(--primary-text-color); }
  .badge.deadline.soon { background: #e8710a; color: #fff; }
  .badge.deadline.urgent { background: #c62828; color: #fff; }
  .list { border-top: 1px solid var(--divider-color); }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 10px 16px 6px;
  }
  .toolbar .spacer { flex: 1; }
  .toolbar button {
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    color: var(--primary-text-color);
    background: none;
  }
  .segments {
    display: inline-flex;
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    overflow: hidden;
  }
  .segments button { border: none; padding: 4px 10px; }
  .segments button + button { border-left: 1px solid var(--divider-color); }
  .segments button.on, .filter.on {
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .filter {
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    padding: 3px 10px;
  }
  .filter.on { border-color: var(--primary-color); }
  .filter .count { opacity: 0.75; margin-left: 4px; }
  .toolbar .mark-read { border: none; color: var(--primary-color); font-weight: 500; padding: 4px 0; }
  .list .row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    cursor: pointer;
  }
  .list .row:hover { background: var(--secondary-background-color); }
  .list .row .pin { flex: none; cursor: inherit; }
  .list .text { min-width: 0; flex: 1; }
  .list .title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .list .row.new .title { font-weight: 600; }
  .list .badges { margin: 2px 0; }
  .list .meta { font-size: 12px; color: var(--secondary-text-color); }
`;

class BekendmakingenMapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._markers = new Map();
    this._key = null;
    this._fitted = false;
    // Per-user data from the frontend storage; null until it has been loaded.
    this._user = null;
    this._userJson = null;
    this._ui = loadUiState();
    this._visible = [];
  }

  static getStubConfig() {
    return { show_list: true };
  }

  static getConfigForm() {
    const s = strings(document.documentElement.lang);
    const select = (options, extra = {}) => ({ select: { mode: "dropdown", options, ...extra } });
    const rubrieken = Object.keys(DEFAULT_STYLES).filter((k) => k !== "kappen");
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "zone", selector: { entity: { domain: "zone" } } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "radius", selector: { number: { min: 0, max: 20000, step: 100, mode: "box", unit_of_measurement: "m" } } },
            { name: "height", selector: { number: { min: 150, max: 1200, step: 10, mode: "box", unit_of_measurement: "px" } } },
          ],
        },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "tiles", selector: select(Object.keys(TILES)) },
            { name: "dark_mode", selector: select(["auto", "light", "dark"]) },
          ],
        },
        {
          name: "attributes",
          selector: { select: { multiple: true, reorder: true, custom_value: true, options: ALL_ATTRIBUTES.map((a) => ({ value: a, label: s.attributes[a] })) } },
        },
        { name: "include_rubrieken", selector: { select: { multiple: true, custom_value: true, options: rubrieken } } },
        { name: "exclude_rubrieken", selector: { select: { multiple: true, custom_value: true, options: rubrieken } } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "open_only", selector: { boolean: {} } },
            { name: "show_list", selector: { boolean: {} } },
            { name: "list_sort", selector: select([...LIST_SORTS, "published"].map((v) => ({ value: v, label: s.sorts[v] }))) },
            { name: "tap_action", selector: select(["popup", "more-info"]) },
          ],
        },
      ],
      computeLabel: (schema) => s.form[schema.name],
    };
  }

  setConfig(config) {
    if (config.tiles && !TILES[config.tiles] && !String(config.tiles).includes("{z}")) {
      throw new Error(`Unknown tiles "${config.tiles}"; use ${Object.keys(TILES).join(", ")} or a URL template`);
    }
    this._config = { ...DEFAULT_CONFIG, ...config };
    this._destroyMap();
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    this._subscribeUserData();
    if (this._map) this._update();
  }

  getCardSize() {
    return Math.ceil(this._config.height / 50) + (this._config.show_list ? 3 : 0);
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  connectedCallback() {
    if (this._mapEl && !this._map) this._initMap();
    this._resizeObserver?.observe(this._mapEl);
    this._subscribeUserData();
    // Keep "3 hours ago" current.
    clearInterval(this._clock);
    this._clock = setInterval(() => this._renderList(), 60000);
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
    clearInterval(this._clock);
    this._unsubscribeUserData();
  }

  get _strings() {
    return strings(this._hass?.locale?.language || this._hass?.language);
  }

  get _language() {
    return this._hass?.locale?.language || this._hass?.language;
  }

  // --- Per-user data: viewed and hidden publications -----------------------------------

  _subscribeUserData() {
    if (this._userSubscription || !this.isConnected || !this._hass?.connection) return;
    this._userSubscription = this._hass.connection
      .subscribeMessage((message) => this._onUserData(message.value), { type: "frontend/subscribe_user_data", key: USER_DATA_KEY })
      .catch((err) => {
        // Without the storage there are no "new" badges and nothing can be hidden.
        console.warn(`${TAG}: per-user data is not available`, err);
        this._userSubscription = null;
        return null;
      });
  }

  _unsubscribeUserData() {
    const subscription = this._userSubscription;
    this._userSubscription = null;
    subscription?.then((unsubscribe) => unsubscribe?.()).catch(() => {});
  }

  _onUserData(value) {
    const data = value && typeof value === "object" ? value : {};
    const user = {
      viewed: data.viewed && typeof data.viewed === "object" ? data.viewed : {},
      hidden: data.hidden && typeof data.hidden === "object" ? data.hidden : {},
      read_before: typeof data.read_before === "string" ? data.read_before : null,
    };
    if (!user.read_before) {
      // First use: what is already there counts as read, only later publications are new.
      user.read_before = new Date().toISOString();
      this._saveUser(user);
      return;
    }
    this._setUser(user);
  }

  _setUser(user) {
    const json = JSON.stringify(user);
    if (json === this._userJson) return;
    this._userJson = json;
    this._user = user;
    this._refresh();
  }

  _saveUser(user) {
    const keepFrom = Date.now() - USER_DATA_RETENTION_MS;
    const prune = (marks) => Object.fromEntries(Object.entries(marks).filter(([, time]) => parseTime(time) >= keepFrom));
    const value = { viewed: prune(user.viewed), hidden: prune(user.hidden), read_before: user.read_before };
    // Show the change right away; the subscription confirms it.
    this._setUser(value);
    this._hass.callWS({ type: "frontend/set_user_data", key: USER_DATA_KEY, value }).catch((err) => this._notify(err));
  }

  _id(stateObj) {
    return stateObj.attributes.identifier || stateObj.entity_id;
  }

  _isNew(stateObj) {
    if (!this._user) return false;
    const firstSeen = parseTime(stateObj.attributes.first_seen);
    return firstSeen > parseTime(this._user.read_before) && !this._user.viewed[this._id(stateObj)];
  }

  _isHidden(stateObj) {
    return Boolean(this._user?.hidden[this._id(stateObj)]);
  }

  _markViewed(entityId) {
    const stateObj = this._hass?.states[entityId];
    if (!stateObj || !this._isNew(stateObj)) return;
    this._saveUser({ ...this._user, viewed: { ...this._user.viewed, [this._id(stateObj)]: new Date().toISOString() } });
  }

  _markAllRead() {
    this._saveUser({ ...this._user, viewed: {}, read_before: new Date().toISOString() });
  }

  _toggleHidden(stateObj) {
    const hidden = { ...this._user.hidden };
    if (hidden[this._id(stateObj)]) delete hidden[this._id(stateObj)];
    else hidden[this._id(stateObj)] = new Date().toISOString();
    this._map?.closePopup();
    this._saveUser({ ...this._user, hidden });
  }

  async _toggleFollowed(stateObj) {
    const service = stateObj.attributes.followed ? "unfollow" : "follow";
    try {
      await this._hass.callService(SOURCE, service, { identifier: stateObj.attributes.identifier });
    } catch (err) {
      this._notify(err);
    }
  }

  _notify(err) {
    const message = `${this._strings.failed} ${err?.message || err}`;
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  // --- Building and updating -------------------------------------------------------------

  _build() {
    const root = this.shadowRoot;
    root.replaceChildren();
    const css = el("link", { rel: "stylesheet", href: `${BASE}leaflet/leaflet.css` });
    this._cssLoaded = new Promise((resolve) => {
      css.onload = resolve;
      css.onerror = resolve;
    });
    this._mapEl = el("div", { class: "map", style: `height: ${Number(this._config.height)}px` });
    this._listEl = el("div", { class: "list" });
    this._card = el("ha-card", { style: "--bm-new-color: #d32f2f; --bm-followed-color: #f9a825" }, this._mapEl, this._listEl);
    if (this._config.title) this._card.header = this._config.title;
    root.append(el("style", {}, CSS), css, this._card);
    this._resizeObserver = new ResizeObserver(() => this._map?.invalidateSize());
    if (this.isConnected) {
      this._resizeObserver.observe(this._mapEl);
      this._initMap();
    }
  }

  async _initMap() {
    const mapEl = this._mapEl;
    if (this._initFor === mapEl) return;
    this._initFor = mapEl;
    try {
      const [L] = await Promise.all([loadLeaflet(), this._cssLoaded]);
      if (mapEl !== this._mapEl) return; // the config changed meanwhile
      this._L = L;
      this._map = L.map(mapEl, { zoomControl: true, attributionControl: true });
      // Vector layers such as the radius need a view; _fit() replaces it once data is there.
      this._map.setView([this._hass?.config.latitude ?? 52.1, this._hass?.config.longitude ?? 5.3], 15);
      const tiles = TILES[this._config.tiles] || { url: this._config.tiles, attribution: "" };
      this._tileLayer = L.tileLayer(tiles.url, {
        attribution: tiles.attribution,
        maxNativeZoom: 19,
        maxZoom: 20,
        className: tiles.photo ? "" : "themed",
      }).addTo(this._map);
      this._layer = L.layerGroup().addTo(this._map);
      this._addRecenterControl();
      this._map.on("popupopen", (e) => {
        this._openId = e.popup._source?.options.entityId;
        // Saving re-renders the markers, which must not happen inside Leaflet's event.
        if (this._openId) setTimeout(() => this._markViewed(this._openId));
      });
      this._map.on("popupclose", () => (this._openId = null));
      if (this._hass) this._update();
    } catch (err) {
      mapEl.replaceChildren(el("div", { class: "message" }, `${this._strings.error} ${err.message}`));
    }
  }

  _destroyMap() {
    this._resizeObserver?.disconnect();
    this._map?.remove();
    this._map = null;
    this._markers.clear();
    this._key = null;
    this._fitted = false;
  }

  _addRecenterControl() {
    const L = this._L;
    const control = L.control({ position: "topleft" });
    control.onAdd = () => {
      const button = el("a", { href: "#", role: "button", title: this._strings.recenter }, el("ha-icon", { icon: "mdi:fit-to-screen-outline" }));
      L.DomEvent.on(button, "click", (e) => {
        L.DomEvent.stop(e);
        this._fit();
      });
      return el("div", { class: "leaflet-bar" }, button);
    };
    control.addTo(this._map);
  }

  /** Publications that pass the card configuration, hidden ones included. */
  _publications() {
    const c = this._config;
    return Object.values(this._hass.states).filter((s) => {
      const a = s.attributes;
      if (!s.entity_id.startsWith("geo_location.") || a.source !== SOURCE) return false;
      if (!Number.isFinite(a.latitude) || !Number.isFinite(a.longitude)) return false;
      if (c.zone && a.zone !== c.zone) return false;
      if (c.include_rubrieken?.length && !c.include_rubrieken.includes(a.rubriek)) return false;
      if (c.exclude_rubrieken?.includes(a.rubriek)) return false;
      if (c.open_only && !isOpen(a.reaction_deadline)) return false;
      return true;
    });
  }

  /** The filters chosen above the list; without a list there are none. */
  get _filters() {
    if (!this._config.show_list) return new Set();
    // "New" and "hidden" need the per-user data.
    return new Set([...this._ui.filters].filter((f) => this._user || (f !== "new" && f !== "hidden")));
  }

  _matches(stateObj, filter) {
    switch (filter) {
      case "new":
        return this._isNew(stateObj);
      case "followed":
        return Boolean(stateObj.attributes.followed);
      case "open":
        return isOpen(stateObj.attributes.reaction_deadline);
      case "hidden":
        return this._isHidden(stateObj);
      default:
        return true;
    }
  }

  /** Publications shown on the map and in the list: hidden ones only with that filter. */
  _applyFilters(publications) {
    const filters = this._filters;
    return publications.filter(
      (s) => this._isHidden(s) === filters.has("hidden") && [...filters].every((f) => this._matches(s, f)),
    );
  }

  _zones(publications) {
    const ids = this._config.zone ? [this._config.zone] : [...new Set(publications.map((s) => s.attributes.zone))];
    return ids.map((id) => this._hass.states[id]).filter((z) => z && Number.isFinite(z.attributes.latitude));
  }

  _isDark() {
    const mode = this._config.dark_mode;
    return mode === "dark" || (mode === "auto" && Boolean(this._hass.themes?.darkMode));
  }

  _style(stateObj) {
    const a = stateObj.attributes;
    const custom = this._config.styles || {};
    const style = {
      ...DEFAULT_STYLES[a.rubriek],
      ...DEFAULT_STYLES[a.activiteit],
      ...custom[a.rubriek],
      ...custom[a.activiteit],
    };
    return { color: style.color || DEFAULT_COLOR, icon: style.icon || a.icon || DEFAULT_ICON };
  }

  _pin(style, extraClass = "") {
    return el("div", { class: `pin ${extraClass}`, style: `--pin-color: ${style.color}` }, el("ha-icon", { icon: style.icon }));
  }

  /** The pin of a publication, with a ring when followed and a dot when new. */
  _publicationPin(stateObj) {
    const pin = this._pin(this._style(stateObj), stateObj.attributes.followed ? "followed" : "");
    if (this._isNew(stateObj)) pin.append(el("span", { class: "dot" }));
    return pin;
  }

  /** Force a re-render, e.g. after the user data or the list choices changed. */
  _refresh() {
    this._key = null;
    if (this._map && this._hass) this._update();
  }

  _update() {
    const all = this._publications();
    const publications = this._applyFilters(all);
    const zones = this._zones(all);
    const dark = this._isDark();
    const key = [
      dark,
      this._language,
      ...zones.map((z) => z.entity_id + z.last_updated),
      ...all.map((s) => s.entity_id + s.last_updated),
    ].join("|");
    if (key === this._key) return;
    this._key = key;

    this._card.classList.toggle("dark", dark);
    const L = this._L;
    const openId = this._openId;
    this._layer.clearLayers();
    this._markers.clear();

    for (const zone of zones) {
      const latlng = [zone.attributes.latitude, zone.attributes.longitude];
      const icon = L.divIcon({ html: this._pin({ color: "", icon: zone.attributes.icon || "mdi:home" }, "zone"), className: "", iconSize: [26, 26], iconAnchor: [13, 13] });
      L.marker(latlng, { icon, interactive: false, keyboard: false }).addTo(this._layer);
      if (this._config.radius) {
        L.circle(latlng, { radius: Number(this._config.radius), className: "radius", weight: 1.5, fillOpacity: 0.06, interactive: false }).addTo(this._layer);
      }
    }

    for (const stateObj of publications) {
      const icon = L.divIcon({ html: this._publicationPin(stateObj), className: "", iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -14] });
      const marker = L.marker([stateObj.attributes.latitude, stateObj.attributes.longitude], {
        icon,
        entityId: stateObj.entity_id,
        title: stateObj.attributes.friendly_name,
        riseOnHover: true,
        // Followed publications stay on top of their neighbours.
        zIndexOffset: stateObj.attributes.followed ? 1000 : 0,
      });
      if (this._config.tap_action === "more-info") {
        marker.on("click", () => this._moreInfo(stateObj.entity_id));
      } else {
        marker.bindPopup(() => this._popup(stateObj.entity_id), {
          maxWidth: 320,
          minWidth: 220,
          maxHeight: Math.max(150, Number(this._config.height) - 70),
        });
      }
      marker.addTo(this._layer);
      this._markers.set(stateObj.entity_id, marker);
    }

    if (!this._fitted) {
      this._fit();
      this._fitted = true;
    }
    if (openId) this._markers.get(openId)?.openPopup();
    this._updateHeader(all);
    this._all = all;
    this._visible = publications;
    this._renderList();
  }

  _updateHeader(all) {
    if (!this._config.title) return;
    const count = all.filter((s) => !this._isHidden(s) && this._isNew(s)).length;
    this._card.header = count ? `${this._config.title} (${this._strings.newCount(count)})` : this._config.title;
  }

  _fit() {
    const L = this._L;
    const points = [];
    this._layer.eachLayer((layer) => {
      if (layer.getBounds) points.push(layer.getBounds().getNorthEast(), layer.getBounds().getSouthWest());
      else if (layer.getLatLng) points.push(layer.getLatLng());
    });
    if (points.length > 1) {
      this._map.fitBounds(L.latLngBounds(points), { padding: [24, 24], maxZoom: 17 });
    } else {
      const center = points[0] || [this._hass.config.latitude, this._hass.config.longitude];
      this._map.setView(center, 15);
    }
  }

  _moreInfo(entityId) {
    this._markViewed(entityId);
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  // --- Formatting --------------------------------------------------------------------------

  _label(stateObj, attribute) {
    const custom = this._config.labels?.[attribute];
    if (custom) return custom;
    const own = this._strings.attributes[attribute];
    if (own) return own;
    return this._hass.formatEntityAttributeName?.(stateObj, attribute) ?? attribute;
  }

  _formatDate(value) {
    const date = parseDate(value);
    if (!date) return String(value);
    return new Intl.DateTimeFormat(this._language, { day: "numeric", month: "long", year: "numeric" }).format(date);
  }

  /** A moment as "3 hours ago", or null when it cannot be read. */
  _relative(value) {
    const time = parseTime(value);
    if (Number.isNaN(time)) return null;
    const seconds = (time - Date.now()) / 1000;
    const format = new Intl.RelativeTimeFormat(this._language, { numeric: "auto" });
    const units = [
      ["year", 31536000],
      ["month", 2592000],
      ["week", 604800],
      ["day", 86400],
      ["hour", 3600],
      ["minute", 60],
    ];
    for (const [unit, size] of units) {
      if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
    }
    return format.format(0, "minute");
  }

  /** A moment as an exact date and time (only a date when no time is known). */
  _exact(value) {
    const time = parseTime(value);
    if (Number.isNaN(time)) return String(value);
    const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
    const options = dateOnly ? { dateStyle: "long" } : { dateStyle: "long", timeStyle: "short" };
    return new Intl.DateTimeFormat(this._language, options).format(new Date(time));
  }

  /** Return the displayed value of an attribute as text or an element, or null to skip it. */
  _value(stateObj, attribute) {
    const value = stateObj.attributes[attribute];
    if (value === null || value === undefined || value === "") return null;
    const s = this._strings;
    switch (attribute) {
      case "published":
        return this._formatDate(value);
      case "first_seen":
        return `${this._relative(value)} (${this._exact(value)})`;
      case "reaction_deadline": {
        const days = daysUntil(value);
        const left = days === null ? "" : days < 0 ? s.expired : days === 0 ? s.today : s.daysLeft(days);
        return left ? `${this._formatDate(value)} (${left})` : this._formatDate(value);
      }
      case "distance_m":
        return value < 1000 ? `${value} m` : `${(value / 1000).toLocaleString(this._language, { maximumFractionDigits: 1 })} km`;
      case "impact": {
        const text = this._hass.formatEntityAttributeValue?.(stateObj, attribute) ?? value;
        return el("span", { class: `impact ${value}` }, String(text));
      }
      case "url":
        return el("a", { href: value, target: "_blank", rel: "noreferrer" }, value.replace(/^https?:\/\//, ""));
      default:
        if (Array.isArray(value)) return value.join(", ");
        if (typeof value === "object") return JSON.stringify(value);
        return String(this._hass.formatEntityAttributeValue?.(stateObj, attribute) ?? value);
    }
  }

  /** Badges for new, followed and an open reaction period. */
  _badges(stateObj) {
    const s = this._strings;
    const badges = [];
    if (this._isNew(stateObj)) badges.push(el("span", { class: "badge new" }, s.new));
    if (stateObj.attributes.followed) {
      badges.push(el("span", { class: "badge followed" }, el("ha-icon", { icon: "mdi:map-marker-star" }), s.followed));
    }
    if (isOpen(stateObj.attributes.reaction_deadline)) {
      const days = daysUntil(stateObj.attributes.reaction_deadline);
      const level = days <= URGENT_DAYS ? "urgent" : days <= SOON_DAYS ? "soon" : "";
      const title = `${s.attributes.reaction_deadline} ${this._formatDate(stateObj.attributes.reaction_deadline)}`;
      badges.push(el("span", { class: `badge deadline ${level}`, title }, el("ha-icon", { icon: "mdi:timer-sand" }), days === 0 ? s.today : s.daysLeft(days)));
    }
    return badges.length ? el("div", { class: "badges" }, badges) : null;
  }

  _popup(entityId) {
    const stateObj = this._hass.states[entityId];
    if (!stateObj) return "";
    const a = stateObj.attributes;
    const s = this._strings;
    const style = this._style(stateObj);
    const rows = [];
    for (const attribute of this._config.attributes) {
      const value = this._value(stateObj, attribute);
      if (value === null) continue;
      // Long texts get the full width under their label.
      const block = attribute === "summary" || attribute === "abstract";
      rows.push(
        el("dt", { class: block ? "block" : "" }, this._label(stateObj, attribute)),
        el("dd", { class: block ? "block" : "" }, value),
      );
    }
    return el(
      "div",
      { class: "popup", style: `--pin-color: ${style.color}` },
      a.rubriek ? el("div", { class: "chip" }, el("ha-icon", { icon: style.icon }), a.rubriek) : null,
      el("h3", {}, a.title || a.friendly_name),
      this._badges(stateObj),
      rows.length ? el("dl", {}, rows) : null,
      el(
        "div",
        { class: "actions" },
        a.url ? el("a", { href: a.url, target: "_blank", rel: "noreferrer" }, s.view) : null,
        el("button", { onclick: () => this._moreInfo(entityId) }, s.details),
        a.identifier
          ? el(
              "button",
              { class: a.followed ? "on" : "", onclick: () => this._toggleFollowed(stateObj) },
              el("ha-icon", { icon: a.followed ? "mdi:map-marker-remove" : "mdi:map-marker-star" }),
              a.followed ? s.unfollow : s.follow,
            )
          : null,
        this._user
          ? el(
              "button",
              { onclick: () => this._toggleHidden(stateObj) },
              el("ha-icon", { icon: this._isHidden(stateObj) ? "mdi:eye" : "mdi:eye-off" }),
              this._isHidden(stateObj) ? s.unhide : s.hide,
            )
          : null,
      ),
    );
  }

  // --- List ----------------------------------------------------------------------------------

  get _sort() {
    const sort = this._ui.sort || this._config.list_sort;
    return [...LIST_SORTS, "published"].includes(sort) ? sort : "distance";
  }

  _setSort(sort) {
    this._ui.sort = sort;
    saveUiState(this._ui);
    this._renderList();
  }

  _toggleFilter(filter) {
    if (this._ui.filters.has(filter)) this._ui.filters.delete(filter);
    else this._ui.filters.add(filter);
    saveUiState(this._ui);
    this._refresh();
  }

  _sorted(publications) {
    const time = (s, attribute) => {
      const t = parseTime(s.attributes[attribute]);
      return Number.isNaN(t) ? null : t;
    };
    const distance = (x, y) => (x.attributes.distance_m ?? 0) - (y.attributes.distance_m ?? 0);
    // Newest first for moments in the past, soonest first for deadlines; unknown ones last.
    const byTime = (attribute, newestFirst) => (x, y) => {
      const xt = time(x, attribute);
      const yt = time(y, attribute);
      if (xt === yt) return distance(x, y);
      if (xt === null) return 1;
      if (yt === null) return -1;
      return newestFirst ? yt - xt : xt - yt;
    };
    const compare = {
      distance,
      first_seen: byTime("first_seen", true),
      published: byTime("published", true),
      reaction_deadline: (x, y) => {
        // Closed reaction periods go after the open ones.
        const open = (s) => isOpen(s.attributes.reaction_deadline);
        return open(y) - open(x) || byTime("reaction_deadline", false)(x, y);
      },
    }[this._sort];
    // Followed publications always come first.
    return [...publications].sort((x, y) => Boolean(y.attributes.followed) - Boolean(x.attributes.followed) || compare(x, y));
  }

  _toolbar() {
    const s = this._strings;
    const all = this._all || [];
    const shown = all.filter((x) => !this._isHidden(x));
    const counts = {
      new: shown.filter((x) => this._isNew(x)).length,
      followed: shown.filter((x) => x.attributes.followed).length,
      open: shown.filter((x) => this._matches(x, "open")).length,
      hidden: all.length - shown.length,
    };
    const filters = LIST_FILTERS.filter((f) => this._user || (f !== "new" && f !== "hidden"))
      // Hidden only shows up once something has been hidden.
      .filter((f) => f !== "hidden" || counts.hidden || this._ui.filters.has("hidden"));
    return el(
      "div",
      { class: "toolbar" },
      el(
        "div",
        { class: "segments", role: "group" },
        [...LIST_SORTS, ...(this._sort === "published" ? ["published"] : [])].map((sort) =>
          el("button", { class: sort === this._sort ? "on" : "", onclick: () => this._setSort(sort) }, s.sorts[sort]),
        ),
      ),
      filters.map((f) =>
        el(
          "button",
          { class: `filter ${this._ui.filters.has(f) ? "on" : ""}`, onclick: () => this._toggleFilter(f) },
          s.filters[f],
          el("span", { class: "count" }, String(counts[f])),
        ),
      ),
      el("span", { class: "spacer" }),
      counts.new ? el("button", { class: "mark-read", onclick: () => this._markAllRead() }, s.markAllRead) : null,
    );
  }

  _renderList() {
    if (!this._listEl || !this._hass || !this._all) return;
    if (!this._config.show_list) {
      this._listEl.replaceChildren();
      this._listEl.hidden = true;
      return;
    }
    this._listEl.hidden = false;
    const s = this._strings;
    const toolbar = this._toolbar();
    if (!this._visible.length) {
      const message = (this._all || []).length ? s.noneFiltered : s.none;
      this._listEl.replaceChildren(toolbar, el("div", { class: "message" }, message));
      return;
    }
    this._listEl.replaceChildren(
      toolbar,
      ...this._sorted(this._visible).map((stateObj) => {
        const a = stateObj.attributes;
        const fetched = this._relative(a.first_seen);
        const meta = [
          a.address || a.rubriek,
          this._value(stateObj, "distance_m"),
          fetched ? el("span", { title: this._exact(a.first_seen) }, s.fetched(fetched)) : null,
        ].filter(Boolean);
        return el(
          "div",
          { class: `row ${this._isNew(stateObj) ? "new" : ""}`, onclick: () => this._select(stateObj.entity_id) },
          this._publicationPin(stateObj),
          el(
            "div",
            { class: "text" },
            el("div", { class: "title", title: a.title || a.friendly_name }, a.title || a.friendly_name),
            this._badges(stateObj),
            el("div", { class: "meta" }, meta.flatMap((part, i) => (i ? [" · ", part] : [part]))),
          ),
        );
      }),
    );
  }

  _select(entityId) {
    if (this._config.tap_action === "more-info") {
      this._moreInfo(entityId);
      return;
    }
    const marker = this._markers.get(entityId);
    if (!marker) return;
    this._map.setView(marker.getLatLng(), Math.max(this._map.getZoom(), 16));
    marker.openPopup();
    this._mapEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

if (!customElements.get(TAG)) {
  customElements.define(TAG, BekendmakingenMapCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "Bekendmakingen kaart",
    description: "Officiële bekendmakingen op de kaart, met icoon per rubriek en een popup met details.",
    documentationURL: "https://github.com/marnixt/officiele-bekendmakingen",
  });
}
