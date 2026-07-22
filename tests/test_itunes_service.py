import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app import models
from app.utilities import schemas
from app.utilities.database import Base
from app.repositories.albums import AlbumRepository
from app.repositories.artists import ArtistRepository
from app.services.itunes import (
    ITunesService,
    build_itunes_search_term,
    parse_release_year,
    search_itunes,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_artist_and_album_models(db_session):
    artist = models.Artist(name="Daft Punk")
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)

    assert artist.id is not None
    assert artist.name == "Daft Punk"

    album = models.Album(
        title="Discovery",
        artist_id=artist.id,
        cover_url="https://example.com/cover.jpg",
        release_year=2001,
    )
    db_session.add(album)
    db_session.commit()
    db_session.refresh(album)

    assert album.id is not None
    assert album.title == "Discovery"
    assert album.cover_url == "https://example.com/cover.jpg"
    assert album.album_url == "https://example.com/cover.jpg"
    assert album.release_year == 2001
    assert album.artist.name == "Daft Punk"
    assert len(artist.albums) == 1
    assert artist.albums[0].title == "Discovery"


def test_artist_and_album_repositories(db_session):
    artist_repo = ArtistRepository(db_session)
    album_repo = AlbumRepository(db_session)

    # Test artist get_or_create
    artist1 = artist_repo.get_or_create("Justice")
    artist2 = artist_repo.get_or_create("Justice")
    assert artist1.id == artist2.id

    # Test album get_or_create
    album1 = album_repo.get_or_create(
        title="Cross",
        artist_id=artist1.id,
        cover_url="https://example.com/cross.jpg",
        release_year=2007,
    )
    album2 = album_repo.get_or_create(
        title="Cross",
        artist_id=artist1.id,
    )
    assert album1.id == album2.id
    assert album2.cover_url == "https://example.com/cross.jpg"
    assert album2.release_year == 2007


def test_build_itunes_search_term():
    assert build_itunes_search_term("Daft Punk", "One More Time") == "Daft Punk One More Time"
    assert (
        build_itunes_search_term("Daft Punk", "One More Time", "Discovery", "2001")
        == "Daft Punk One More Time Discovery 2001"
    )
    assert build_itunes_search_term(" Artist ", " Title ", None, "") == "Artist Title"


def test_parse_release_year():
    assert parse_release_year("2021-03-12T07:00:00Z") == 2021
    assert parse_release_year("1999") == 1999
    assert parse_release_year(None) is None
    assert parse_release_year("invalid") is None


@pytest.mark.anyio
async def test_search_itunes_success():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "resultCount": 1,
        "results": [
            {
                "artistName": "Daft Punk",
                "trackName": "One More Time",
                "collectionName": "Discovery",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/100x100bb.jpg",
                "releaseDate": "2001-03-12T08:00:00Z",
                "trackViewUrl": "https://music.apple.com/track/123",
                "primaryGenreName": "Dance",
            }
        ],
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    result = await search_itunes(
        title="One More Time",
        artist="Daft Punk",
        album="Discovery",
        client=mock_client,
    )

    assert result is not None
    assert result.artist_name == "Daft Punk"
    assert result.track_title == "One More Time"
    assert result.album_name == "Discovery"
    assert result.cover_url == "https://is1-ssl.mzstatic.com/image/thumb/600x600bb.jpg"
    assert result.release_year == 2001
    assert result.genre == "Dance"


@pytest.mark.anyio
async def test_itunes_service_fetch_and_persist(db_session):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "resultCount": 1,
        "results": [
            {
                "artistName": "Kavinsky",
                "trackName": "Nightcall",
                "collectionName": "OutRun",
                "artworkUrl100": "https://example.com/100x100bb.jpg",
                "releaseDate": "2013-02-22T00:00:00Z",
            }
        ],
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    service = ITunesService(db_session)
    result = await service.fetch_and_persist(
        title="Nightcall",
        artist="Kavinsky",
        album="OutRun",
        client=mock_client,
    )

    assert result is not None
    assert result.artist_id is not None
    assert result.album_id is not None

    artist_db = db_session.get(models.Artist, result.artist_id)
    album_db = db_session.get(models.Album, result.album_id)

    assert artist_db.name == "Kavinsky"
    assert album_db.title == "OutRun"
    assert album_db.cover_url == "https://example.com/600x600bb.jpg"
    assert album_db.release_year == 2013


def test_itunes_search_api_endpoint(client):
    mock_result = schemas.ITunesSearchResult(
        artist_name="The Weeknd",
        track_title="Blinding Lights",
        album_name="After Hours",
        cover_url="https://example.com/cover600.jpg",
        release_date="2020-03-20T00:00:00Z",
        release_year=2020,
        itunes_url="https://music.apple.com/track/456",
        genre="R&B",
        artist_id=1,
        album_id=1,
    )

    with patch(
        "app.services.itunes.ITunesService.fetch_and_persist",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = client.get(
            "/itunes/search",
            params={
                "artist": "The Weeknd",
                "title": "Blinding Lights",
                "album": "After Hours",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["artist_name"] == "The Weeknd"
        assert data["track_title"] == "Blinding Lights"
        assert data["album_name"] == "After Hours"
        assert data["cover_url"] == "https://example.com/cover600.jpg"
        assert data["release_year"] == 2020


@pytest.mark.anyio
async def test_search_itunes_no_results():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"resultCount": 0, "results": []}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    result = await search_itunes(
        title="Unknown Track",
        artist="Unknown Artist",
        client=mock_client,
    )
    assert result is None


@pytest.mark.anyio
async def test_search_itunes_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.HTTPError("Network failure")

    result = await search_itunes(
        title="Error Track",
        artist="Error Artist",
        client=mock_client,
    )
    assert result is None


def test_repository_getters(db_session):
    artist_repo = ArtistRepository(db_session)
    album_repo = AlbumRepository(db_session)

    artist = artist_repo.create(schemas.ArtistCreate(name="M83"))
    assert artist_repo.get_by_id(artist.id).name == "M83"
    assert artist_repo.get_by_name("M83").id == artist.id
    assert artist_repo.get_by_name("Nonexistent") is None

    album = album_repo.create(
        schemas.AlbumCreate(
            title="Hurry Up, We're Dreaming",
            artist_id=artist.id,
            cover_url="https://example.com/cover.jpg",
            release_year=2011,
        )
    )
    assert album_repo.get_by_id(album.id).title == "Hurry Up, We're Dreaming"
    assert album_repo.get_by_title_and_artist("Hurry Up, We're Dreaming", artist.id).id == album.id
    assert album_repo.get_by_title_and_artist("Unknown Album", artist.id) is None


def test_itunes_search_api_endpoint_404(client):
    with patch(
        "app.services.itunes.ITunesService.fetch_and_persist",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.get(
            "/itunes/search",
            params={"artist": "Nonexistent", "title": "Nothing"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No information found on iTunes for the requested track"


@pytest.mark.anyio
async def test_itunes_service_db_cache_hit(db_session):
    artist_repo = ArtistRepository(db_session)
    album_repo = AlbumRepository(db_session)

    artist = artist_repo.create(schemas.ArtistCreate(name="Daft Punk"))
    album = album_repo.create(
        schemas.AlbumCreate(
            title="Discovery",
            artist_id=artist.id,
            cover_url="https://example.com/cached_discovery.jpg",
            release_year=2001,
        )
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    service = ITunesService(db_session)

    result = await service.fetch_and_persist(
        title="One More Time",
        artist="Daft Punk",
        album="Discovery",
        client=mock_client,
    )

    assert result is not None
    assert result.cached is True
    assert result.cover_url == "https://example.com/cached_discovery.jpg"
    assert result.album_name == "Discovery"
    assert mock_client.get.call_count == 0


@pytest.mark.anyio
async def test_itunes_service_cache_miss_then_hit_cycle(db_session):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "resultCount": 1,
        "results": [
            {
                "artistName": "Gorillaz",
                "trackName": "Feel Good Inc.",
                "collectionName": "Demon Days",
                "artworkUrl100": "https://example.com/gorillaz_100x100bb.jpg",
                "releaseDate": "2005-05-11T00:00:00Z",
            }
        ],
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    service = ITunesService(db_session)

    # First call: Cache Miss -> calls iTunes and populates DB
    result1 = await service.fetch_and_persist(
        title="Feel Good Inc.",
        artist="Gorillaz",
        album="Demon Days",
        client=mock_client,
    )
    assert result1 is not None
    assert result1.cached is False
    assert mock_client.get.call_count == 1

    # Second call: Cache Hit -> reads directly from DB
    result2 = await service.fetch_and_persist(
        title="Feel Good Inc.",
        artist="Gorillaz",
        album="Demon Days",
        client=mock_client,
    )
    assert result2 is not None
    assert result2.cached is True
    assert result2.cover_url == "https://example.com/gorillaz_600x600bb.jpg"
    assert mock_client.get.call_count == 1


