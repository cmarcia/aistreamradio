import pytest
from app import models, schemas


def test_genre_model_instantiation():
    genre = models.Genre(name="Synthwave", description="80s Electronic Synth Music")
    assert genre.name == "Synthwave"
    assert genre.description == "80s Electronic Synth Music"


def test_station_model_instantiation():
    genre = models.Genre(name="Synthwave", description="Electronic")
    station = models.Station(
        name="Cyber FM",
        frequency="108.0 FM",
        genre=genre,
        stream_url="https://example.com/live.m3u8",
        metadata_url="https://example.com/meta.json",
    )
    assert station.name == "Cyber FM"
    assert station.frequency == "108.0 FM"
    assert station.genre.name == "Synthwave"
    assert station.stream_url == "https://example.com/live.m3u8"
    assert station.metadata_url == "https://example.com/meta.json"


def test_station_schema_default_urls():
    payload = schemas.StationCreate(name="Default Radio", frequency="99.9 FM")
    assert payload.name == "Default Radio"
    assert payload.frequency == "99.9 FM"
    assert payload.stream_url == "https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8"
    assert payload.metadata_url == "https://d3d4yli4hf5bmh.cloudfront.net/metadata.json"


def test_station_schema_custom_urls():
    payload = schemas.StationCreate(
        name="Custom Radio",
        frequency="88.8 FM",
        genre_id=1,
        stream_url="https://custom.stream/live.m3u8",
        metadata_url="https://custom.stream/meta.json",
    )
    assert payload.genre_id == 1
    assert payload.stream_url == "https://custom.stream/live.m3u8"
    assert payload.metadata_url == "https://custom.stream/meta.json"
