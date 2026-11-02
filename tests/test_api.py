"""Tests for the SRU response parser."""

from datetime import date

import pytest

from custom_components.officiele_bekendmakingen.api import SruError, parse_response, wkt_centroid

RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<sru:searchRetrieveResponse
    xmlns:overheidwetgeving="http://standaarden.overheid.nl/wetgeving/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sru="http://docs.oasis-open.org/ns/search-ws/sruResponse"
    xmlns:gzd="http://standaarden.overheid.nl/sru">
  <sru:version>2.0</sru:version>
  <sru:numberOfRecords>2</sru:numberOfRecords>
  <sru:records>
    <sru:record><sru:recordData><gzd:gzd>
      <gzd:originalData><overheidwetgeving:meta>
        <overheidwetgeving:owmskern>
          <dcterms:identifier>gmb-2026-1</dcterms:identifier>
          <dcterms:title>Besluit omgevingsvergunning, Voorbeeldstraat 1</dcterms:title>
          <dcterms:type scheme="OVERHEIDop.Rubriek">omgevingsvergunning</dcterms:type>
          <dcterms:creator scheme="OVERHEID.Gemeente">Voorbeeldstad</dcterms:creator>
        </overheidwetgeving:owmskern>
        <overheidwetgeving:owmsmantel>
          <dcterms:date>2026-10-23</dcterms:date>
          <dcterms:abstract>Z2026-1 - kappen van een eik</dcterms:abstract>
        </overheidwetgeving:owmsmantel>
        <overheidwetgeving:tpmeta>
          <overheidwetgeving:activiteit>kappen</overheidwetgeving:activiteit>
          <overheidwetgeving:datumEindeReactietermijn>2026-12-02</overheidwetgeving:datumEindeReactietermijn>
          <overheidwetgeving:gebiedsmarkering><overheidwetgeving:Vlak>
            <overheidwetgeving:locatiegebied>POLYGON((5.0 51.0,5.2 51.0,5.2 51.2,5.0 51.2))</overheidwetgeving:locatiegebied>
          </overheidwetgeving:Vlak></overheidwetgeving:gebiedsmarkering>
        </overheidwetgeving:tpmeta>
      </overheidwetgeving:meta></gzd:originalData>
      <gzd:enrichedData>
        <gzd:url>https://repository.overheid.nl/frbr/officielepublicaties/gmb/2026/gmb-2026-1/1/xml/gmb-2026-1.xml</gzd:url>
        <gzd:preferredUrl>https://zoek.officielebekendmakingen.nl/gmb-2026-1.html</gzd:preferredUrl>
      </gzd:enrichedData>
    </gzd:gzd></sru:recordData></sru:record>
    <sru:record><sru:recordData><gzd:gzd>
      <gzd:originalData><overheidwetgeving:meta>
        <overheidwetgeving:owmskern>
          <dcterms:identifier>gmb-2026-2</dcterms:identifier>
        </overheidwetgeving:owmskern>
      </overheidwetgeving:meta></gzd:originalData>
    </gzd:gzd></sru:recordData></sru:record>
  </sru:records>
</sru:searchRetrieveResponse>
"""


def test_parse_response_full_record():
    total, items = parse_response(RESPONSE)

    assert total == 2
    item = items[0]
    assert item.identifier == "gmb-2026-1"
    assert item.rubriek == "omgevingsvergunning"
    assert item.activiteit == "kappen"
    assert item.authority == "Voorbeeldstad"
    assert item.published == date(2026, 10, 23)
    assert item.reaction_deadline == date(2026, 12, 2)
    assert item.url == "https://zoek.officielebekendmakingen.nl/gmb-2026-1.html"
    assert item.locations == (pytest.approx((51.1, 5.1)),)
    assert item.abstract == "Z2026-1 - kappen van een eik"
    assert item.content_url.endswith("/xml/gmb-2026-1.xml")


def test_parse_response_minimal_record():
    _, items = parse_response(RESPONSE)

    item = items[1]
    assert item.title == "gmb-2026-2"
    assert item.locations == ()
    assert item.reaction_deadline is None
    assert item.abstract is None
    assert item.content_url is None


def test_wkt_centroid_point_is_lat_lon():
    assert wkt_centroid("POINT (5.08 51.56)") == (51.56, 5.08)


def test_wkt_centroid_without_coordinates():
    assert wkt_centroid("POLYGON EMPTY") is None


def test_parse_response_diagnostic_raises():
    diagnostic = (
        '<searchRetrieveResponse xmlns="http://docs.oasis-open.org/ns/search-ws/sruResponse">'
        "<version>2.0</version><diagnostics/></searchRetrieveResponse>"
    )
    with pytest.raises(SruError):
        parse_response(diagnostic)


def test_parse_response_invalid_xml_raises():
    with pytest.raises(SruError):
        parse_response("not xml")
