/*
 * Map card for the Officiële Bekendmakingen integration.
 *
 * Shows the publications (geo_location entities with source "officiele_bekendmakingen")
 * with an icon and colour per rubriek, and a popup with the attributes chosen in the card
 * configuration. Plain custom element without a build step; Leaflet is shipped alongside.
 */

const TAG = "bekendmakingen-map-card";
const SOURCE = "officiele_bekendmakingen";
const BASE = new URL(".", import.meta.url).href;

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
  "rubriek",
  "activiteit",
  "authority",
  "published",
  "reaction_deadline",
  "distance_m",
  "url",
];

const DEFAULT_CONFIG = {
  height: 400,
  tiles: "pdok",
  dark_mode: "auto",
  attributes: ["summary", "abstract", "rubriek", "activiteit", "authority", "published", "reaction_deadline", "distance_m"],
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
    today: "laatste dag",
    daysLeft: (n) => (n === 1 ? "nog 1 dag" : `nog ${n} dagen`),
    expired: "verlopen",
    recenter: "Alles tonen",
    error: "De kaart kon niet worden geladen.",
    attributes: {
      summary: "Samenvatting",
      impact: "Impact",
      abstract: "Omschrijving",
      rubriek: "Rubriek",
      activiteit: "Activiteit",
      authority: "Bevoegd gezag",
      published: "Gepubliceerd",
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
    today: "last day",
    daysLeft: (n) => (n === 1 ? "1 day left" : `${n} days left`),
    expired: "closed",
    recenter: "Show all",
    error: "The map could not be loaded.",
    attributes: {
      summary: "Summary",
      impact: "Impact",
      abstract: "Description",
      rubriek: "Category",
      activiteit: "Activity",
      authority: "Authority",
      published: "Published",
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

function daysUntil(value) {
  const date = parseDate(value);
  if (!date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((date - today) / 86400000);
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
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 14px;
    cursor: pointer;
    text-decoration: none;
  }
  .popup .actions a { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .popup .actions button {
    background: none;
    border: 1px solid var(--divider-color);
    color: var(--primary-text-color);
  }
  .list { border-top: 1px solid var(--divider-color); }
  .list .row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    cursor: pointer;
  }
  .list .row:hover { background: var(--secondary-background-color); }
  .list .row .pin { flex: none; cursor: inherit; }
  .list .text { min-width: 0; }
  .list .title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .list .meta { font-size: 12px; color: var(--secondary-text-color); }
`;

class BekendmakingenMapCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._markers = new Map();
    this._key = null;
    this._fitted = false;
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
            { name: "list_sort", selector: select(["distance", "reaction_deadline", "published"]) },
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
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
  }

  get _strings() {
    return strings(this._hass?.locale?.language || this._hass?.language);
  }

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
    this._card = el("ha-card", {}, this._mapEl, this._listEl);
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
      this._map.on("popupopen", (e) => (this._openId = e.popup._source?.options.entityId));
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

  _publications() {
    const c = this._config;
    return Object.values(this._hass.states).filter((s) => {
      const a = s.attributes;
      if (!s.entity_id.startsWith("geo_location.") || a.source !== SOURCE) return false;
      if (!Number.isFinite(a.latitude) || !Number.isFinite(a.longitude)) return false;
      if (c.zone && a.zone !== c.zone) return false;
      if (c.include_rubrieken?.length && !c.include_rubrieken.includes(a.rubriek)) return false;
      if (c.exclude_rubrieken?.includes(a.rubriek)) return false;
      if (c.open_only && !(daysUntil(a.reaction_deadline) >= 0)) return false;
      return true;
    });
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

  _update() {
    const publications = this._publications();
    const zones = this._zones(publications);
    const dark = this._isDark();
    const key = [
      dark,
      this._hass.locale?.language,
      ...zones.map((z) => z.entity_id + z.last_updated),
      ...publications.map((s) => s.entity_id + s.last_updated),
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
      const style = this._style(stateObj);
      const icon = L.divIcon({ html: this._pin(style), className: "", iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -14] });
      const marker = L.marker([stateObj.attributes.latitude, stateObj.attributes.longitude], {
        icon,
        entityId: stateObj.entity_id,
        title: stateObj.attributes.friendly_name,
        riseOnHover: true,
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
    this._renderList(publications);
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
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

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
    const language = this._hass.locale?.language || this._hass.language;
    return new Intl.DateTimeFormat(language, { day: "numeric", month: "long", year: "numeric" }).format(date);
  }

  /** Return the displayed value of an attribute as text or an element, or null to skip it. */
  _value(stateObj, attribute) {
    const value = stateObj.attributes[attribute];
    if (value === null || value === undefined || value === "") return null;
    const s = this._strings;
    switch (attribute) {
      case "published":
        return this._formatDate(value);
      case "reaction_deadline": {
        const days = daysUntil(value);
        const left = days === null ? "" : days < 0 ? s.expired : days === 0 ? s.today : s.daysLeft(days);
        return left ? `${this._formatDate(value)} (${left})` : this._formatDate(value);
      }
      case "distance_m": {
        const language = this._hass.locale?.language || this._hass.language;
        return value < 1000 ? `${value} m` : `${(value / 1000).toLocaleString(language, { maximumFractionDigits: 1 })} km`;
      }
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

  _popup(entityId) {
    const stateObj = this._hass.states[entityId];
    if (!stateObj) return "";
    const a = stateObj.attributes;
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
      rows.length ? el("dl", {}, rows) : null,
      el(
        "div",
        { class: "actions" },
        a.url ? el("a", { href: a.url, target: "_blank", rel: "noreferrer" }, this._strings.view) : null,
        el("button", { onclick: () => this._moreInfo(entityId) }, this._strings.details),
      ),
    );
  }

  _renderList(publications) {
    if (!this._config.show_list) {
      this._listEl.replaceChildren();
      this._listEl.hidden = true;
      return;
    }
    this._listEl.hidden = false;
    if (!publications.length) {
      this._listEl.replaceChildren(el("div", { class: "message" }, this._strings.none));
      return;
    }
    const sortKey = this._config.list_sort;
    const sorted = [...publications].sort((x, y) => {
      if (sortKey === "distance") return (x.attributes.distance_m ?? 0) - (y.attributes.distance_m ?? 0);
      const xv = x.attributes[sortKey] || "9999";
      const yv = y.attributes[sortKey] || "9999";
      // Deadlines soonest first, publications newest first.
      return sortKey === "published" ? yv.localeCompare(xv) : xv.localeCompare(yv);
    });
    this._listEl.replaceChildren(
      ...sorted.map((stateObj) => {
        const a = stateObj.attributes;
        const meta = [a.rubriek, this._value(stateObj, "distance_m"), a.reaction_deadline ? this._value(stateObj, "reaction_deadline") : null]
          .filter(Boolean)
          .join(" · ");
        return el(
          "div",
          { class: "row", onclick: () => this._select(stateObj.entity_id) },
          this._pin(this._style(stateObj)),
          el("div", { class: "text" }, el("div", { class: "title" }, a.title || a.friendly_name), el("div", { class: "meta" }, meta)),
        );
      }),
    );
  }

  _select(entityId) {
    const marker = this._markers.get(entityId);
    if (!marker) return;
    if (this._config.tap_action === "more-info") {
      this._moreInfo(entityId);
      return;
    }
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
