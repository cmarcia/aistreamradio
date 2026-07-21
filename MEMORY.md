# AI Stream Radio — Project Memory & Knowledge Base

This memory file contains comprehensive knowledge of **AI Stream Radio** ("The Source"), including its architecture, database schemas, API contracts, frontend design system, testing strategies, and operational guidelines.

---

## 1. Executive Summary & Core Requirements

**AI Stream Radio** is a prototype live radio streaming web application featuring:
- **HLS Audio Streaming:** High-fidelity live broadcast audio player with low-latency configuration.
- **Live Metadata Polling:** Client periodically polls stream metadata (every 15s) to update active track title, artist, album, and signal format.
- **Song Rating System:** Thumbs up / thumbs down rating per track, constrained to one rating per song per listener session (`listener_id` stored in browser `localStorage`).
- **Dislike Mute-Skipping:** Downvoting a song immediately mutes audio until the live metadata changes to a new track, then automatically unmutes.
- **Persistent Dislikes & Cover Snapshots:** Disliked tracks are saved with a timestamp and a base64 snapshot of the cover art captured via `<canvas>` at the moment of voting.
- **Paginated Disliked Songs List:** Paginated list API and UI tab showing listener's disliked song history.
- **Clickable Station Navigation:** Clicking any station name in the "Previous tracks" or "Songs you disliked" list cards tunes into that station, starts playback immediately, and updates the header station dropdown with a `✓` checkmark indicator.
- **Cyberpunk / Dark Sci-Fi HUD Design:** Futuristic UI with glassmorphism, animated signal visualizer, glowing indicators, and smooth state transitions.
- **Strict Data Decoupling Rule:** Zero hardcoded station lists, dictionaries, or SVG string blocks in Python source files (`app/main.py`). All initial station datasets, genres, SVG cover templates, and default colors MUST be loaded from external data/config files (`data/initial_stations.json`, `app/static/Images/station-cover-template.svg`, `app/config.py`).

---

## 2. Architecture & Technology Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python >= 3.12)
- **ASGI Server:** Uvicorn (`app.main:app --reload`)
- **Database:** SQLite (persisted at `data/radiostation.db`)
- **ORM:** SQLAlchemy 2.x declarative models
- **Validation & Settings:** Pydantic v2 & Pydantic-Settings (`.env` file support)
- **Environment & Tools:** Managed via `uv` or standard Python `venv` + `pip`

### Frontend
- **Structure:** Pure HTML5, CSS3, Vanilla ES6 JavaScript (No client-side framework/bundler)
- **Modular JS:** 
  - `util.js`: Centralized `apiFetch()`, `apiFetchOrWarn()`, `renderList()`, and canvas screenshot helper `captureCoverSnapshot()`.
  - `player.js`: Audio / HLS.js playback state, mute toggle, signal visualizer animation loop.
  - `rating.js`: Thumbs up/down state, rating submission, dislike mute-skipping monitor.
  - `disliked.js`: Disliked songs list fetching, rendering, and pagination state management.
  - `formatters.js`: Pure helper functions (`formatTime`, `computeDislikedPagination`, `addToHistory`).
  - `main.js`: Core initialization script wiring modules together on DOM ready.
- **Audio Streaming:** [HLS.js](https://github.com/video-dev/hls.js) MSE with native HLS fallback for Safari.
- **Design & Styling:** Custom CSS3 (`style.css`), dark synthwave aesthetic, Orbitron & Rajdhani Google Fonts.

### Infrastructure & Containerization
- **Docker & Compose:** `Dockerfile` & `docker-compose.yml`
- **Docker Volume Note:** SQLite DB uses named Docker volume `radiostation_data` (`/code/data/`) to prevent macOS VirtioFS file-locking issues (`OperationalError: attempt to write a readonly database`).

---

## 3. Codebase File Structure

```
aistreamradio/
├── app/
│   ├── __init__.py
│   ├── config.py             # Pydantic Settings (DATABASE_URL, APP_NAME, DISLIKED_SONGS_PAGE_SIZE)
│   ├── database.py           # SQLAlchemy engine, SessionLocal, get_db dependency
│   ├── main.py               # FastAPI application, routes, table creation, rating logic
│   ├── models.py             # SQLAlchemy ORM models (Station, Song, SongRating)
│   ├── schemas.py            # Pydantic schemas for requests, responses, pagination
│   └── static/               # Frontend static assets
│       ├── index.html        # Main HUD web interface layout
│       ├── CSS/              # CSS stylesheets
│       │   └── style.css     # Cyberpunk dark theme CSS system
│       ├── Images/           # Image assets
│       │   ├── default-cover.svg
│       │   └── logo.png
│       ├── Script/           # JavaScript source files
│       │   ├── main.js       # App bootstrapper & module coordinator
│       │   ├── player.js     # Audio player & visualizer engine
│       │   ├── rating.js     # Rating controls & mute-skipping state
│       │   ├── disliked.js   # Paginated disliked track list logic
│       │   ├── util.js       # Shared fetch & UI helper utilities
│       │   └── formatters.js # Pure formatting & pagination functions
│       └── tests/            # Vitest unit tests for frontend logic
│           └── formatters.test.js
├── data/                     # Local SQLite DB storage directory (git-ignored)
├── documentation/            # Extended system & design documentation
│   ├── system_documentation.md
│   └── design_update.md
├── tests/                    # Backend Pytest test suite
│   ├── conftest.py
│   ├── test_disliked_songs_integration.py
│   ├── test_song_rating_integration.py
│   ├── test_song_rating_persistence.py
│   ├── test_song_rating_unit.py
│   ├── test_static_assets_integration.py
│   └── test_stations_integration.py
├── .env.example              # Environment variables template
├── Dockerfile                # Backend container definition
├── docker-compose.yml        # Multi-container orchestrator setup
├── package.json              # Node.js dev dependencies (Vitest)
├── pyproject.toml            # Python dependencies (FastAPI, SQLAlchemy, Pytest, etc.)
├── tasks.md                  # Project refactoring & task tracking log
└── MEMORY.md                 # Project knowledge base (this file)
```

---

## 4. Database Schema & Data Models

### `genres` Table (`app/models.py`)
- `id`: `Integer` (Primary Key, Indexed)
- `name`: `String` (Not Null, Unique)
- `description`: `String` (Nullable)
- `created_at`: `DateTime(timezone=True)` (Default: UTC now)
- **Relationship:** `stations` -> `list[Station]` (One-to-Many back-populated by `Station.genre`)

### `stations` Table (`app/models.py`)
- `id`: `Integer` (Primary Key, Indexed)
- `name`: `String` (Not Null)
- `frequency`: `String` (Not Null)
- `genre_id`: `Integer` (ForeignKey `genres.id`, Nullable, Indexed)
- `stream_url`: `String` (Not Null, default HLS stream URL)
- `metadata_url`: `String` (Nullable, default metadata JSON endpoint)
- `created_at`: `DateTime(timezone=True)` (Default: UTC now)
- **Relationship:** `genre` -> `Genre` (Many-to-One linked via `genre_id`)

### `songs` Table (`app/models.py`)
- `id`: `Integer` (Primary Key, Indexed)
- `artist`: `String` (Not Null)
- `title`: `String` (Not Null)
- `cover_image`: `Text` (Nullable, Base64 data URL captured when rated)
- **Constraint:** `UniqueConstraint("artist", "title", name="uq_song_artist_title")`

### `song_ratings` Table (`app/models.py`)
- `id`: `Integer` (Primary Key, Indexed)
- `song_id`: `Integer` (ForeignKey `songs.id`, Indexed)
- `listener_id`: `String` (Indexed, Browser UUID)
- `rating`: `String` ("up" | "down")
- `created_at`: `DateTime(timezone=True)` (Default: UTC now)
- **Constraint:** `UniqueConstraint("song_id", "listener_id", name="uq_rating_song_listener")`

---

## 5. API Reference

| Endpoint | Method | Params / Payload | Description |
|---|---|---|---|
| `/` | `GET` | — | Serves main single-page web app (`index.html`) |
| `/health` | `GET` | — | Health check (`{"status": "ok"}`) |
| `/genres` | `GET` | — | Returns list of musical genres |
| `/genres` | `POST` | `GenreCreate` JSON | Creates a new musical genre |
| `/genres/{id}` | `GET` | `id: int` | Gets details for a specific genre |
| `/stations` | `GET` | — | Returns list of radio stations with linked genre (auto-seeds defaults if empty) |
| `/stations` | `POST` | `StationCreate` JSON | Creates a new station record |
| `/stations/{id}` | `GET` | `id: int` | Gets details for a specific station |
| `/stations/{id}/stream` | `GET` | `id: int` | Proxies/redirects live audio stream for a station |
| `/stations/{id}/metadata` | `GET` | `id: int` | Returns current metadata feed for a station |
| `/stations/{id}/cover` | `GET` | `id: int` | Returns station artwork SVG image |
| `/songs/rating` | `GET` | `artist`, `title`, `listener_id?` | Retrieves song rating totals (thumbs up/down) & user's rating |
| `/songs/rating` | `POST` | `SongRatingCreate` JSON | Rates song (`up` or `down`). Returns HTTP 409 if already rated by listener |
| `/songs/disliked` | `GET` | `listener_id`, `page` (default 1), `page_size` (default 5) | Paginated list of listener's downvoted tracks with cover images |

---

## 6. Development & Testing Commands

### Backend Virtual Environment & Tests
```bash
# Rebuild virtualenv if interpreter path changes
python3 -m venv .venv
.venv/bin/pip install -r pyproject.toml

# Run all backend unit & integration tests (45 tests)
.venv/bin/pytest -v
```

### Frontend Tests (Vitest)
```bash
# Run all frontend unit tests (19 tests)
npm test
```

### Running Local Development Server
```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Running with Docker Compose
```bash
docker compose up --build -d
```

---

## 7. Key Architecture Design Notes & Security Rules

1. **Base64 Image Size Limit:** `SongRatingCreate.cover_image` schema enforces `max_length=2_000_000` to prevent memory inflation DoS.
2. **CORS & Image Canvas Capture:** `<img id="coverArt">` includes `crossorigin="anonymous"` to prevent canvas tainting during screenshot capture.
3. **Database Concurrency:** FastAPI uses request-scoped sessions (`get_db`). SQLite uses `check_same_thread=False`.
4. **Listener Identification:** Client generates a persistent UUID in `localStorage.getItem('listenerId')`.
