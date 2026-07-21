# Technical Specification: Track Metadata & Album Cover Art Auto-Lookup

**Feature Title:** Track Metadata & Album Cover Art Auto-Lookup Service  
**Status:** Approved Technical Design  
**Version:** 1.0  
**Target Project:** AI Stream Radio (`aistreamradio`)  
**Target Files:**
- Backend Router: [`app/routers/itunes.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/routers/itunes.py)
- Backend Service: [`app/services/itunes.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/services/itunes.py)
- Repositories: [`app/repositories/albums.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/albums.py), [`app/repositories/artists.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/artists.py)
- Schemas: [`app/schemas.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/schemas.py)
- Frontend Logic: [`app/static/Script/main.js`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/main.js)
- Test Suite: [`tests/test_itunes_service.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_itunes_service.py)

---

## 1. System Architecture & Component Interactions

The feature provides a unified backend endpoint (`GET /itunes/search`) that implements a **two-tier lookup strategy**:
1. **Tier 1 (Database Cache Hit):** First checks the local database (`artists` and `albums` tables). If matching album metadata and `cover_url` exist, the record is immediately returned without making an external HTTP network request.
2. **Tier 2 (Database Cache Miss & iTunes Fetch):** If no matching record exists in the local database, the backend queries the external **iTunes Search API**, parses higher-resolution cover art (`600x600bb`), persists the `Artist` and `Album` records into the database, and returns the response to the client.

```mermaid
graph TD
    subgraph Client [Browser - main.js]
        PM[Metadata Poller] -->|Detect Track Change| TC[onTrackChanged]
        TC -->|GET /itunes/search| API[FastAPI Router /itunes/search]
        API -->|Update DOM| UI[DOM: #coverArt & #albumName]
    end

    subgraph Backend [FastAPI - ITunesService]
        API --> SVC[ITunesService.fetch_and_persist]
        SVC -->|1. Query DB| Repo[AlbumRepository & ArtistRepository]
        
        alt Database Cache Hit
            Repo -->|Album Record Found| SVC
        else Database Cache Miss
            SVC -->|2. HTTP Search Query| iTunes[iTunes Search API]
            iTunes -->|JSON Result| SVC
            SVC -->|3. Persist Artist & Album| Repo
        end
        
        SVC -->|Return ITunesSearchResult| API
    end

    subgraph Database [SQLite - radiostation.db]
        Repo -->|SELECT / INSERT| DB[(artists & albums tables)]
    end
```

---

## 2. Backend Technical Implementation Details

### 2.1 Database Repositories Extensions

#### `AlbumRepository` ([`app/repositories/albums.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/albums.py))
Add a lookup method to search for existing album records by artist name and track/album title using case-insensitive matching:

```python
def get_by_artist_and_title(self, artist_name: str, album_title: str | None = None, track_title: str | None = None) -> models.Album | None:
    """
    Searches for an Album record by matching artist name and album title (or track title fallback).
    Uses case-insensitive string comparison.
    """
    query = (
        select(models.Album)
        .join(models.Artist)
        .where(func.lower(models.Artist.name) == artist_name.strip().lower())
    )
    if album_title:
        query = query.where(func.lower(models.Album.title) == album_title.strip().lower())
    
    result = self.db.scalar(query)
    if result and result.cover_url:
        return result
    return None
```

---

### 2.2 Service Layer Logic (`ITunesService`)

Modify `fetch_and_persist` in [`app/services/itunes.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/services/itunes.py) to check local DB first before executing external HTTP calls:

```python
class ITunesService:
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
        # Step 1: Check Database Cache First (Cache Hit Path)
        existing_album = self.album_repo.get_by_artist_and_title(
            artist_name=artist, album_title=album
        )
        if existing_album and existing_album.cover_url:
            logger.info(f"Database Cache HIT for artist '{artist}' and album/track '{album or title}'")
            artist_obj = self.artist_repo.get_by_id(existing_album.artist_id) if existing_album.artist_id else None
            return schemas.ITunesSearchResult(
                artist_id=existing_album.artist_id,
                artist_name=artist_obj.name if artist_obj else artist,
                album_id=existing_album.id,
                album_name=existing_album.title,
                cover_url=existing_album.cover_url,
                release_date=str(existing_album.release_year) if existing_album.release_year else release_date,
                release_year=existing_album.release_year,
                cached=True,
            )

        # Step 2: Database Cache Miss -> Call iTunes Search API
        logger.info(f"Database Cache MISS for '{artist} - {title}'. Querying iTunes Search API...")
        result = await search_itunes(
            title=title,
            artist=artist,
            release_date=release_date,
            album=album,
            client=client,
        )

        if result is None:
            return None

        # Step 3: Persist newly fetched records into DB
        artist_obj = self.artist_repo.get_or_create(name=result.artist_name)
        result.artist_id = artist_obj.id

        if result.album_name:
            album_obj = self.album_repo.get_or_create(
                title=result.album_name,
                artist_id=artist_obj.id,
                cover_url=result.cover_url,
                release_year=result.release_year,
            )
            result.album_id = album_obj.id

        result.cached = False
        return result
```

---

### 2.3 Schema Adjustments (`app/schemas.py`)

Add a `cached` boolean flag to `ITunesSearchResult` schema in [`app/schemas.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/schemas.py):

```python
class ITunesSearchResult(BaseModel):
    artist_id: int | None = None
    artist_name: str
    album_id: int | None = None
    album_name: str | None = None
    cover_url: str | None = None
    release_date: str | None = None
    release_year: int | None = None
    itunes_url: str | None = None
    genre: str | None = None
    cached: bool = False
```

---

## 3. Frontend Integration Details (`app/static/Script/main.js`)

In [`app/static/Script/main.js`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/main.js), update `applyMetadata()` to trigger an asynchronous cover art fetch whenever a new track is detected:

```javascript
async function fetchTrackCoverArt(artist, title, album) {
  if (!artist || !title) return;

  const activeTrackKey = currentTrackKey; // Capture current key for race condition check
  const params = new URLSearchParams({ artist, title });
  if (album) params.append("album", album);

  try {
    const data = await apiFetch(`/itunes/search?${params.toString()}`);
    
    // Race condition guard: Ensure track hasn't changed while request was in-flight
    if (currentTrackKey !== activeTrackKey) return;

    if (data && data.cover_url) {
      coverArt.src = data.cover_url;
      if (data.album_name) {
        let yearStr = data.release_year ? ` (${data.release_year})` : "";
        albumName.textContent = `${data.album_name}${yearStr}`;
      }
    }
  } catch (err) {
    logger.warn("iTunes album cover lookup failed, retaining fallback artwork:", err);
    // Retain station fallback cover art already assigned by applyMetadata
  }
}
```

---

## 4. Race Condition & Edge Case Handling

1. **Fast Track Changes (Race Condition Guard):**
   - If stream metadata polls rapidly or user changes stations while an external iTunes query is in-flight, the frontend compares `activeTrackKey` before applying results to DOM elements `#coverArt` or `#albumName`.
2. **Special Characters in Track / Artist Titles:**
   - Query parameters are encoded via `URLSearchParams` to handle symbols, spaces, and non-Latin characters (e.g. `artist="Beyoncé"`, `title="Texas Hold 'Em"`).
3. **External Request Timeout & Failure:**
   - `httpx.AsyncClient` timeout is capped at `5.0` seconds. If iTunes API is unavailable or times out, `search_itunes` logs a warning and returns `None` (HTTP 404), triggering standard station fallback art without breaking UI playback.

---

## 5. Testing & Verification Plan

### Backend Unit & Integration Tests ([`tests/test_itunes_service.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_itunes_service.py))

1. **Test DB Cache Hit:**
   - Pre-populate database with an `Artist` and `Album` containing a `cover_url`.
   - Call `ITunesService.fetch_and_persist()`.
   - Assert `result.cached == True`.
   - Verify 0 network requests were dispatched to `httpx.AsyncClient`.

2. **Test DB Cache Miss & Persistence:**
   - Clear DB tables.
   - Mock external `httpx` response with sample iTunes API payload.
   - Call `ITunesService.fetch_and_persist()`.
   - Assert `result.cached == False`.
   - Verify new `Artist` and `Album` rows exist in DB.

3. **Test Subsequent Request (Cache Miss -> Hit Cycle):**
   - Execute query once (creates DB records).
   - Execute exact same query second time.
   - Assert second call returns `cached == True`.

### Frontend Tests ([`app/static/tests/formatters.test.js`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/tests/formatters.test.js))
- Run `npm test` to verify zero regression in track key calculation and history logic.
