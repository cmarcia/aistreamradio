# AI Stream Radio — System Documentation

Welcome to the comprehensive system documentation for **AI Stream Radio**, a prototype radio streaming web application featuring a responsive, cyberpunk-themed HUD dashboard, real-time metadata tracking, user rating stats, and stream-mute skipping for disliked tracks.

---

## 1. Requirements

### Functional Requirements
* **Audio Streaming:** Play the live audio broadcast seamlessly (using standard high-fidelity HLS stream).
* **Live Metadata Display:** Periodically poll the broadcast metadata stream (every 15 seconds) and update the active track, artist, album, and format quality indicators without pausing audio.
* **Track Ratings:** Allow users to give thumbs-up or thumbs-down ratings to the currently playing song (limited to one rating per track per user session).
* **Disliked Tracks Skipping:** When a user downvotes (dislikes) a song, the system mutes the live stream until a new track starts playing, then automatically unmutes it.
* **Persistent Dislikes:** Keep a list of all disliked tracks for the active user, complete with their recorded timestamp and a base64 cover art thumbnail snapshot captured at the moment of downvoting.
* **Paginated View:** The disliked tracks list must be paginated (defaulting to 5 items per page) and queryable via backend parameters.
* **Session Tracking:** Persistently identify unique listeners using a lightweight, browser-local UUID.

### Non-Functional Requirements
* **Low Latency:** Utilize low-latency HLS stream configurations for instantaneous play/pause responses.
* **Responsive Visual Aesthetic:** The interface must use a futuristic dark/synthwave design system with clear visual focus states and smooth transitions.
* **Modular Codebase:** Separate Javascript concerns (player, ratings, lists, formatters) for testability.
* **Lightweight Footprint:** Avoid heavy client-side bundlers or heavy third-party frameworks.

---

## 2. Technical Specification

### Backend Tech Stack
* **Web Server:** [FastAPI](https://fastapi.tiangolo.com/) served by [Uvicorn](https://www.uvicorn.org/) (ASGI).
* **Database & ORM:** [SQLite](https://sqlite.org/) with [SQLAlchemy 2.x](https://www.sqlalchemy.org/) ORM.
* **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/) for data transfer schemas and environment-based configuration.
* **Dependency Manager:** astral-sh [uv](https://docs.astral.sh/uv/) for Python environment isolation and locked dependency installations.

### Frontend Tech Stack
* **Structure & UI Logic:** Pure HTML5 and Vanilla ES6 JavaScript split into domain-specific modules.
* **Streaming Engine:** [HLS.js](https://github.com/video-dev/hls.js) for MSE (Media Source Extensions) streaming, falling back to browser-native HLS on Safari/iOS.
* **Styles:** Custom CSS3 utilizing CSS custom properties (variables), absolute-positioned blurred layout orbs, cyberpunk scan grids, and responsive flexbox/grid containers.
* **Fonts:** Geometric geometric/humanist Google Fonts: *Orbitron* (timers/headers), *Rajdhani* (subtitles/labels), and *Inter* (body text).

---

## 3. System Architecture

Below is the architectural data flow map for **AI Stream Radio**:

```mermaid
graph TD
    subgraph Client [Browser Client (HTML5 / Vanilla JS)]
        UI[HUD Dashboard / Glassmorphic UI]
        AV[Cybernetic Signal Visualizer]
        AP[Audio Stream Player (Hls.js)]
        LS[localStorage - listenerId]
    end

    subgraph CDN [CloudFront CDN]
        Stream["HLS Stream (live.m3u8)"]
        MetaFeed["Live Metadata (metadata.json)"]
    end

    subgraph Backend [FastAPI Application Server]
        API["FastAPI Endpoints (main.py)"]
        ORM["SQLAlchemy ORM (models.py)"]
        iTunesSvc["iTunes Search Service (services/itunes.py)"]
    end

    subgraph DB [SQLite Database]
        Tables["Tables (stations, songs, ratings, artists, albums)"]
    end

    subgraph iTunesAPI [External Services]
        iTunes["iTunes Search API (itunes.apple.com)"]
    end

    %% Audio and Metadata Streams
    Stream -->|Lossless audio| AP
    MetaFeed -->|Polled metadata every 15s| UI
    AP -->|Active playback triggers| AV

    %% API communication
    UI -->|GET /songs/rating| API
    UI -->|POST /songs/rating (Base64 Cover)| API
    UI -->|GET /songs/disliked| API
    UI -->|GET /stations| API
    UI -->|GET /itunes/search| API
    API --> iTunesSvc
    iTunesSvc -->|HTTP Search Query| iTunes

    %% DB relations
    API --> ORM
    iTunesSvc --> ORM
    ORM -->|Read/Write| Tables
```

---

## 4. The Tasks Tracker

### Completed Refactoring & Feature Additions
* [x] **iTunes Search & Persistence Service:** Implemented `ITunesService` ([app/services/itunes.py](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/services/itunes.py)) querying `https://itunes.apple.com/search?term=artist+song+album&entity=song&limit=1` to retrieve track details, higher-resolution cover art (`600x600bb`), album name, artist name, and release date/year.
* [x] **Track Metadata & Album Cover Art Auto-Lookup Service:** Implemented automatic 2-tier database cache hit & iTunes fallback lookup service for new songs. Checks local database (`artists` and `albums` tables) first via `AlbumRepository.get_by_artist_name_and_title`, queries external iTunes API on cache miss, persists results into DB, and updates frontend HUD `#coverArt` and `#albumName`.
* [x] **Database Refactoring — Song & Artist Many-to-Many Relationship:** Refactored `Song` and `Artist` database schema by introducing the `song_artists` association table. Removed direct string `artist` column from `songs` table, populated `artists` table with 25 distinct artist records (backfilling all missing artists from existing songs), and established a clean Many-to-Many relationship between `Song` and `Artist`.


* [x] **Artist & Album Database Tables:** Added `Artist` (`artists`) and `Album` (`albums`) models in [app/models.py](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/models.py) with repository patterns ([app/repositories/artists.py](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/artists.py), [app/repositories/albums.py](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/albums.py)) and API endpoints (`GET /itunes/search`).
* [x] **Modularize Frontend:** Decoupled `app.js` into domain-focused files in `app/static/Script/`: [player.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/player.js), [rating.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/rating.js), [disliked.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/disliked.js), [util.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/util.js), [formatters.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/formatters.js), and [main.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/main.js).
* [x] **Clickable Station Navigation:** Made station names in "Previous tracks" and "Songs you disliked" list cards interactive buttons. Clicking any station tunes directly to that station, starts playback, and selects it in the top station dropdown with a `✓` checkmark indicator.
* [x] **Organize Static Assets:** Organized JavaScript files into [app/static/Script/](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script), image assets into [app/static/Images/](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Images), and stylesheets into [app/static/CSS/](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/CSS).
* [x] **Add Frontend & Backend Tests:** Created unit-test suites in [formatters.test.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/tests/formatters.test.js) (Vitest) and [test_itunes_service.py](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_itunes_service.py) (pytest).
* [x] **Centralize API Calls:** Refactored repetitive fetch blocks using `apiFetch()` and `apiFetchOrWarn()` helpers in [util.js](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/util.js).
* [x] **Implement Futuristic Dark Theme:** Overhauled [style.css](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/CSS/style.css) with an interactive dark sci-fi hud layout, glassmorphic styling cards, and pulsing drop-shadows.
* [x] **Signal Visualizer:** Integrated an equalizer interface displaying 16 gradient bars that dynamically animate while playback is active and reset during pauses/mutes.

---

## 5. Deployment Guide

The application supports both native execution and containerized deployment.

### Option A: Native Execution (Recommended for Local Dev)

#### 1. Setup Environment
Ensure you have `python` (>= 3.12) and Astral's `uv` installed. Sync dependencies and build virtual environment:
```bash
uv sync
```

#### 2. Configure Environment Variables
You can create a `.env` file in the root directory to customize values (defaults shown):
```ini
DATABASE_URL=sqlite:///./data/radiostation.db
APP_NAME="AI Stream Radio API"
DISLIKED_SONGS_PAGE_SIZE=5
```

#### 3. Run Server
Start the Uvicorn ASGI server:
```bash
uv run --python 3.13 uvicorn app.main:app --reload
```
Access the application on [http://localhost:8000/](http://localhost:8000/).

---

### Option B: Docker Compose (Containerized Deployment)

#### 1. Build and Launch
Build and start the container in the background:
```bash
docker compose up --build -d
```

> [!IMPORTANT]
> **Docker Volume Warning (macOS file lock):** 
> The database is stored in a named Docker volume `radiostation_data` inside the container at `/code/data/` rather than a direct host bind-mount. 
> On Docker Desktop for Mac, mounting an active SQLite database directly from the host routes file locks through VirtioFS/gRPC-FUSE, which can spuriously throw `sqlite3.OperationalError: attempt to write a readonly database` during concurrent backend writes.

---

## 6. Test Cases & Verification

The project includes thorough, automated end-to-end integration and unit test suites:

### 1. Backend Python Tests (pytest)
Located in `/tests`, covering persistent DB integration:
* **`test_itunes_service.py`:** Tests iTunes API search queries, cover URL resolution (`600x600bb`), release year parsing, `Artist` & `Album` database models and relationships, repository helpers, and `GET /itunes/search` API endpoint.
* **`test_stations_integration.py`:** Tests station creation and details fetch.
* **`test_song_rating_integration.py`:** Asserts rating aggregations, checks user constraints, and validates rating inputs.
* **`test_disliked_songs_integration.py`:** Asserts pagination offsets, page size overrides, and cover art retrieval rules.
* **`test_static_assets_integration.py`:** Ensures all JS files are linked and served in correct dependency order.

To run:
```bash
uv run pytest -v
```

### 2. Frontend JS Tests (Vitest)
Located in `app/static/tests`, verifying UI logic functions:
* **`formatTime`:** Validates conversions of seconds under/over a minute and bounds checks.
* **`computeDislikedPagination`:** Validates pagination bounds, disables pager buttons when appropriate, and calculates exact page splits.
* **`addToHistory`:** Ensures session history appends new tracks up to the limit without mutating active variables.

To run:
```bash
npm test
```

---

## 7. Security Review & Report

A security review was conducted on the prototype architecture:

### 🔒 Core Security Mechanisms
1. **Pydantic Schema Validation:** Incoming payloads are rigidly parsed on input. The maximum string size for base64 cover images is capped at **2,000,000 characters** in [schemas.py](file:///Users/charliemarciano/workspace/projects/radiostation/app/schemas.py) (`cover_image` Field constraint) to block potential buffer inflation or denial-of-service (DoS) exploits.
2. **CORS Headers & Image Tainting:** The `<img id="coverArt">` element uses `crossorigin="anonymous"`. This ensures that when the canvas capture tool (`captureCoverSnapshot()`) generates base64 images from the live stream art, the browser does not taint the canvas or throw security exceptions.
3. **Database Unique Constraints:** 
   * **Song Uniqueness:** The `songs` table enforces a `uq_song_artist_title` constraint.
   * **Single Rating Constraint:** The `song_ratings` table uses a `uq_rating_song_listener` unique composite constraint of `(song_id, listener_id)`, preventing double voting or DB inflation by a single user.
4. **SQL Injection Prevention:** Backend database queries use SQLAlchemy's parameter binding `select().where()` syntax, rendering SQL injection vectors impossible.
5. **Path Traversal Protection:** Static file routes are mounted strictly inside the container workspace path (`/code/app/static`), preventing system path traversal bypasses.
