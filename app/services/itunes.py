from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from app import schemas
from app.logging_config import logger
from app.repositories.albums import AlbumRepository
from app.repositories.artists import ArtistRepository

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def build_itunes_search_term(
    artist: str,
    title: str,
    album: str | None = None,
    release_date: str | None = None,
) -> str:
    """
    Builds the formatted search query term string for iTunes API.
    Combines non-empty values into space-separated string e.g. "artist song album".
    """
    parts = [p.strip() for p in (artist, title, album, release_date) if p and p.strip()]
    return " ".join(parts)


def parse_release_year(release_date_raw: str | None) -> int | None:
    """
    Extracts a 4-digit release year integer from a release date string
    (e.g., '2020-05-15T07:00:00Z' or '2020').
    """
    if not release_date_raw:
        return None

    s = str(release_date_raw).strip()
    if not s:
        return None

    # Handle standard ISO timestamp or date prefix YYYY
    try:
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.year
    except Exception:
        pass
    return None


async def search_itunes(
    title: str,
    artist: str,
    release_date: str | None = None,
    album: str | None = None,
    timeout: float = 5.0,
    client: httpx.AsyncClient | None = None,
) -> schemas.ITunesSearchResult | None:
    """
    Queries iTunes Search API (https://itunes.apple.com/search?term=artist+song+album&entity=song&limit=1)
    and returns parsed information including cover artwork, album name, artist name, and release date/year.
    """
    term = build_itunes_search_term(
        artist=artist, title=title, album=album, release_date=release_date
    )
    if not term:
        return None

    params = {
        "term": term,
        "entity": "song",
        "limit": 1,
    }

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        should_close_client = True

    try:
        logger.info(f"Querying iTunes Search API with term: '{term}'")
        response = await client.get(ITUNES_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            logger.info(f"No results found on iTunes for search term: '{term}'")
            return None

        item = results[0]

        # Extract higher-resolution cover art URL if artworkUrl100 is available
        cover_url = item.get("artworkUrl100")
        if cover_url and "100x100bb" in cover_url:
            cover_url = cover_url.replace("100x100bb", "600x600bb")

        extracted_release_date = item.get("releaseDate") or release_date
        release_year = parse_release_year(extracted_release_date)

        result = schemas.ITunesSearchResult(
            artist_name=item.get("artistName") or artist,
            track_title=item.get("trackName") or title,
            album_name=item.get("collectionName") or album,
            cover_url=cover_url,
            release_date=extracted_release_date,
            release_year=release_year,
            itunes_url=item.get("trackViewUrl") or item.get("collectionViewUrl"),
            genre=item.get("primaryGenreName"),
        )
        return result
    except httpx.HTTPError as exc:
        logger.warning(f"HTTP error searching iTunes for term '{term}': {exc}")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error searching iTunes API for '{term}': {exc}", exc_info=True)
        return None
    finally:
        if should_close_client:
            await client.aclose()


class ITunesService:
    """Service class for fetching iTunes song metadata and persisting Artist & Album records."""

    def __init__(self, db: Session):
        self.db = db
        self.artist_repo = ArtistRepository(db)
        self.album_repo = AlbumRepository(db)

    async def fetch_and_persist(
        self,
        title: str,
        artist: str,
        release_date: str | None = None,
        album: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> schemas.ITunesSearchResult | None:
        """
        Retrieves track metadata from iTunes and persists/links Artist and Album records into the database.
        """
        result = await search_itunes(
            title=title,
            artist=artist,
            release_date=release_date,
            album=album,
            client=client,
        )

        if result is None:
            return None

        # Create or retrieve Artist in database
        artist_obj = self.artist_repo.get_or_create(name=result.artist_name)
        result.artist_id = artist_obj.id

        # Create or retrieve Album in database if album name exists
        if result.album_name:
            album_obj = self.album_repo.get_or_create(
                title=result.album_name,
                artist_id=artist_obj.id,
                cover_url=result.cover_url,
                release_year=result.release_year,
            )
            result.album_id = album_obj.id

        return result
