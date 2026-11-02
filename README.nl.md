# Officiële Bekendmakingen voor Home Assistant

Volg officiële bekendmakingen van de overheid (vergunningen, evenementen, verkeersbesluiten,
bomenkap, …) bij jou in de buurt, via de openbare SRU-zoekdienst van
[officielebekendmakingen.nl](https://www.officielebekendmakingen.nl).

*English: see [README.md](https://github.com/marnixt/officiele-bekendmakingen/blob/main/README.md).*

> Status: vroege ontwikkeling (0.4.3).

## Functies
- Kies een zone (thuis of een andere zone), een straal eromheen en hoeveel dagen je terug wilt
  kijken. De integratie zoekt dan de gemeenten, provincies en waterschappen waarvan het gebied
  binnen de straal ligt (via de [PDOK Locatieserver](https://www.pdok.nl)), zodat je kunt kiezen
  welke je volgt. De overheden waarin de zone zelf ligt, zijn al aangevinkt.
- Sensor **Bekendmakingen in de buurt**: het aantal bekendmakingen binnen de straal, met de
  dichtstbijzijnde (titel, rubriek, activiteit, afstand, link) als attributen.
- Sensor **Eerstvolgende reactietermijn**: het eerstvolgende einde van een termijn voor een
  zienswijze of bezwaar.
- **Kaart**: elke bekendmaking binnen de straal (maximaal 50, dichtstbijzijnde eerst) is een
  `geo_location`-entiteit in het midden van het aangegeven gebied, met een icoon per rubriek (en
  activiteit, bijvoorbeeld een boom bij kappen). Entiteiten verschijnen en verdwijnen vanzelf.
- **Dashboardkaart** `custom:bekendmakingen-map-card`, wordt automatisch geladen: gekleurde markers
  per rubriek, een popup met de velden die je kiest, een optionele lijst onder de kaart en
  Nederlandse achtergrondkaarten van PDOK (Kadaster).
- **AI-samenvattingen** (optioneel): kies in de opties een
  [AI-taak](https://www.home-assistant.io/integrations/ai_task/)-entiteit, dan krijgt elke
  bekendmaking binnen de straal een korte samenvatting en een inschatting van de impact
  (laag/middel/hoog).
- **Event** `officiele_bekendmakingen_new_publication` voor elke bekendmaking die nieuw binnen de
  straal verschijnt, met de samenvatting als die aan staat. Bekendmakingen die er al waren toen
  je de integratie instelde, worden niet gemeld.
- **Opties**: wijzig achteraf de straal, de periode, de overheden, de AI-taak en de taal van de
  samenvattingen via *Instellingen → Apparaten & diensten → Officiële Bekendmakingen → Configureren*.

## Kaart
De integratie heeft een eigen kaart. Voeg hem toe via de kaartkiezer (*Bekendmakingen kaart*)
en stel hem in via de UI, of in YAML:

```yaml
type: custom:bekendmakingen-map-card
title: Bekendmakingen
zone: zone.home          # alleen bekendmakingen van deze zone; weglaten toont alle zones
radius: 1000             # teken de zoekstraal rond de zone (meter)
height: 400
tiles: pdok              # pdok, pdok_grijs, pdok_luchtfoto, osm of een {z}/{x}/{y}-URL
dark_mode: auto          # auto, light of dark
show_list: true          # lijst onder de kaart
list_sort: distance      # distance, reaction_deadline of published
open_only: false         # alleen bekendmakingen waarop je nog kunt reageren
tap_action: popup        # popup of more-info
attributes:              # velden in de popup, in deze volgorde
  - summary
  - impact
  - abstract
  - rubriek
  - activiteit
  - authority
  - published
  - reaction_deadline
  - distance_m
labels:                  # optioneel: eigen namen voor velden in de popup
  reaction_deadline: Zienswijze tot
include_rubrieken: []    # alleen deze rubrieken
exclude_rubrieken:
  - verkiezingen
styles:                  # optioneel: kleur en icoon per rubriek of activiteit
  evenementenvergunning:
    color: "#9c27b0"
  kappen:
    icon: mdi:pine-tree
```

Elk attribuut van een bekendmaking kan onder `attributes`; datums, afstand en impact worden
netjes weergegeven, en bij de reactietermijn staat hoeveel dagen je nog hebt. De popup heeft een
knop naar de bekendmaking en een knop naar het standaard detailvenster.

De standaard kaart van Home Assistant werkt ook, maar toont op de markers de eerste letters van
elke titel:

```yaml
type: map
geo_location_sources:
  - officiele_bekendmakingen
```

## AI-samenvattingen
1. Stel een AI-integratie in die een AI-taak-entiteit levert (bijvoorbeeld OpenAI, Google
   Gemini, Anthropic of Ollama).
2. Open de opties van een zone en kies die entiteit bij *AI-taak voor samenvattingen*.
3. Kies eventueel een andere *Taal van de samenvattingen*; standaard is dat Nederlands, de taal
   van de bekendmakingen. Na een wijziging worden samenvattingen in een andere taal opnieuw
   gemaakt.

De integratie haalt dan van elke bekendmaking binnen de straal één keer de tekst op en vraagt
de AI-taak om een samenvatting en een impact. Samenvattingen worden bewaard, dus een bekendmaking
wordt nooit twee keer samengevat. Nieuwe bekendmakingen worden samengevat voordat ze gemeld
worden; oudere worden ingehaald met tien per uur, dichtstbijzijnde eerst. Mislukt een
samenvatting, dan blijft alleen de samenvatting leeg en wordt het een uur later opnieuw
geprobeerd. Na een herstart wacht de integratie tot vijf minuten tot de AI-taak beschikbaar is.

Bij een AI-dienst in de cloud is elke samenvatting één betaalde aanvraag. Ter indicatie: 100
samenvattingen kosten ongeveer 1 cent met gpt-6-luna.

## Melding bij nieuwe bekendmakingen
De eventdata bevat `title`, `rubriek`, `activiteit`, `abstract`, `authority`, `published`,
`reaction_deadline`, `distance_m`, `url`, `summary`, `impact`, `identifier`, `zone` en
`entry_id`. `summary` en `impact` zijn leeg als AI-samenvattingen uit staan.

```yaml
triggers:
  - trigger: event
    event_type: officiele_bekendmakingen_new_publication
actions:
  - action: notify.notify
    data:
      title: "Nieuwe bekendmaking ({{ trigger.event.data.distance_m }} m)"
      message: "{{ trigger.event.data.summary or trigger.event.data.title }}"
      data:
        url: "{{ trigger.event.data.url }}"
```

## Installatie
1. Voeg deze repository in HACS toe als aangepaste repository (categorie: Integratie).
2. Installeer **Officiële Bekendmakingen** en herstart Home Assistant.
3. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen** en zoek op
   *Officiële Bekendmakingen*.

## Ontwikkeling
```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # Windows: .venv\Scripts\pip
ruff check custom_components tests
python -m pytest
```
