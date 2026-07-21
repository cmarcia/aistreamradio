# AI Stream Radio

Prototype website backend: **FastAPI** web server + **SQLite** database, running under **Docker Compose**.

## Stack

- **Web server:** FastAPI served by Uvicorn (ASGI), with `--reload` for live development.
- **Database:** SQLite, stored at `/code/data/radiostation.db` inside the container, persisted in the named Docker volume `radiostation_data` (not a host bind-mount — see note below).
- **ORM:** SQLAlchemy 2.x.

## Layout

```
app/
  config.py     # settings (DATABASE_URL, etc.) via pydantic-settings
  database.py   # SQLAlchemy engine, session, Base, get_db dependency
  models.py     # ORM models (Station)
  schemas.py    # Pydantic request/response schemas
  main.py       # FastAPI app + routes
  static/       # Frontend static assets
    CSS/        # CSS stylesheets (style.css)
    Images/     # Image assets (default-cover.svg, logo.png)
    Script/     # Modular JS files (main.js, player.js, rating.js, etc.)
    tests/      # Frontend unit tests (formatters.test.js)
data/           # SQLite file lives here (git-ignored)
pyproject.toml  # dependencies (managed with uv)
uv.lock
Dockerfile
docker-compose.yml
```

## Run with Docker

```bash
docker compose up --build
```

API is then at http://localhost:8000 — interactive docs at http://localhost:8000/docs.

> **Note:** the SQLite data directory is a named Docker volume, not a host
> bind-mount. On Docker Desktop for Mac, bind-mounting a SQLite file from the
> host routes file locks through the VirtioFS/gRPC-FUSE overlay, which can
> spuriously report the database as read-only mid-write (seen as
> `sqlite3.OperationalError: attempt to write a readonly database` in
> container logs). Use `docker compose exec web sqlite3 data/radiostation.db`
> or copy the volume out if you need to inspect the DB from the host.

## Run natively (without Docker)

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run --python 3.13 uvicorn app.main:app --reload
```

## Endpoints

| Method | Path               | Description          |
|--------|--------------------|----------------------|
| GET    | `/health`          | Health check         |
| GET    | `/stations`        | List all stations    |
| POST   | `/stations`        | Create a station     |
| GET    | `/stations/{id}`   | Get one station      |
| GET    | `/songs/rating`    | Get a song's thumbs up/down totals + your rating |
| POST   | `/songs/rating`    | Rate a song up/down (once per listener)          |
| GET    | `/songs/disliked`  | Paginated list of songs you've disliked          |

## Configuration

Settings are read from environment variables / `.env` (see `app/config.py`):

| Variable                    | Default | Description |
|------------------------------|---------|--------------|
| `DATABASE_URL`               | `sqlite:///./data/radiostation.db` | DB connection string |
| `APP_NAME`                   | `AI Stream Radio API` | FastAPI app title |
| `DISLIKED_SONGS_PAGE_SIZE`   | `5` | Default page size for `GET /songs/disliked`. Callers can also override per-request with `?page_size=`. |

## Tests

Unit and integration tests use `pytest` with an isolated in-memory SQLite database (no `data/radiostation.db` involved).

```bash
uv run pytest -v
```

### Example

```bash
curl -X POST http://localhost:8000/stations \
  -H 'Content-Type: application/json' \
  -d '{"name":"KEXP","frequency":"90.3 FM","genre":"Alternative"}'

curl http://localhost:8000/stations
```
