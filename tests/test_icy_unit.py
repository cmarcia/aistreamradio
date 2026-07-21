import pytest
from app.utilities.icy import parse_icy_payload


def test_parse_icy_payload_artist_and_title():
    payload = "StreamTitle='UADA - Our Pale Departure';StreamUrl='https://somafm.com/logos/512/metal512.png';"
    result = parse_icy_payload(payload)
    assert result is not None
    assert result["artist"] == "UADA"
    assert result["title"] == "Our Pale Departure"
    assert result["has_track_info"] is True
    assert result["cover_url"] == "https://somafm.com/logos/512/metal512.png"


def test_parse_icy_payload_title_only():
    payload = "StreamTitle='Beethoven Symphony No. 5';"
    result = parse_icy_payload(payload)
    assert result is not None
    assert result["artist"] == ""
    assert result["title"] == "Beethoven Symphony No. 5"
    assert result["has_track_info"] is True
    assert result["cover_url"] is None


def test_parse_icy_payload_empty_title():
    payload = "StreamTitle='';"
    result = parse_icy_payload(payload)
    assert result is None


def test_parse_icy_payload_generic_ignored_titles():
    assert parse_icy_payload("StreamTitle='kz';") is None
    assert parse_icy_payload("StreamTitle='CDN';") is None
    assert parse_icy_payload("StreamTitle='Live Stream';") is None


def test_parse_icy_payload_malformed():
    assert parse_icy_payload(None) is None
    assert parse_icy_payload("NoStreamTitleHere") is None
