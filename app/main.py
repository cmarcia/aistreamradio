import json
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.config import settings
from app.database import Base, engine, get_db
from app.icy import fetch_icy_metadata

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/genres", response_model=list[schemas.Genre])
def list_genres(db: Session = Depends(get_db)):
    return db.scalars(select(models.Genre)).all()


@app.post("/genres", response_model=schemas.Genre, status_code=201)
def create_genre(payload: schemas.GenreCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.Genre).where(models.Genre.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Genre already exists")
    genre = models.Genre(**payload.model_dump())
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre


@app.get("/genres/{genre_id}", response_model=schemas.Genre)
def get_genre(genre_id: int, db: Session = Depends(get_db)):
    genre = db.get(models.Genre, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


@app.get("/stations/{station_id}/stream")
async def get_station_stream(station_id: int, db: Session = Depends(get_db)):
    station = db.get(models.Station, station_id)
    if station is None or not station.stream_url:
        raise HTTPException(status_code=404, detail="Station or stream URL not found")

    url = station.stream_url

    if ".m3u8" in url or "/hls" in url:
        return RedirectResponse(url=url)

    async def stream_generator():
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@app.get("/stations/{station_id}/metadata")
async def get_station_metadata(station_id: int, db: Session = Depends(get_db)):
    station = db.scalar(
        select(models.Station).where(models.Station.id == station_id).options(joinedload(models.Station.genre))
    )
    if station is None:
        return {
            "artist": f"Station {station_id}",
            "title": None,
            "album": "Radio Broadcast",
            "genre": "Live Music",
            "has_track_info": False,
            "date": "2026",
            "bit_depth": 16,
            "sample_rate": 44100,
            "cover_url": f"/stations/{station_id}/cover",
        }

    # Attempt live ICY stream metadata probe
    if station.stream_url and station.stream_url.startswith("http"):
        live_meta = await fetch_icy_metadata(station.stream_url, timeout=3.0)
        if live_meta and live_meta.get("title"):
            station.current_artist = live_meta["artist"] or station.name
            station.current_title = live_meta["title"]
            station.has_track_info = True
            if live_meta.get("cover_url"):
                station.cover_url = live_meta["cover_url"]
            db.commit()

    genre_name = station.genre.name if station.genre else "Live Music"
    cover_url = station.cover_url or f"/stations/{station.id}/cover"

    return {
        "artist": station.current_artist or station.name,
        "title": station.current_title if station.has_track_info else None,
        "album": station.current_album or "Radio Broadcast",
        "genre": genre_name,
        "has_track_info": station.has_track_info,
        "date": station.date or "2026",
        "bit_depth": station.bit_depth or 16,
        "sample_rate": station.sample_rate or 44100,
        "cover_url": cover_url,
    }


COVER_TEMPLATE_PATH = STATIC_DIR / "Images" / "station-cover-template.svg"


@app.get("/stations/{station_id}/cover")
def get_station_cover(station_id: int, db: Session = Depends(get_db)):
    station = db.scalar(
        select(models.Station).where(models.Station.id == station_id).options(joinedload(models.Station.genre))
    )
    if station is None:
        bg1 = settings.default_primary_color
        bg2 = settings.default_secondary_color
        title = f"STATION {station_id}"
        subtitle = "RADIO STREAM"
    else:
        bg1 = station.primary_color or settings.default_primary_color
        bg2 = station.secondary_color or settings.default_secondary_color
        title = station.name
        genre_name = station.genre.name if station.genre else ""
        subtitle = f"{station.frequency} • {genre_name}".strip(" •")

    template = COVER_TEMPLATE_PATH.read_text(encoding="utf-8")
    svg = template.format(bg1=bg1, bg2=bg2, title=title, subtitle=subtitle)

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


INITIAL_STATIONS_PATH = Path(__file__).parent.parent / "data" / "initial_stations.json"


def _seed_initial_data(db: Session):
    if not INITIAL_STATIONS_PATH.exists():
        return

    data = json.loads(INITIAL_STATIONS_PATH.read_text(encoding="utf-8"))
    genres_map = {}

    for g_data in data.get("genres", []):
        name = g_data["name"]
        g = db.scalar(select(models.Genre).where(models.Genre.name == name))
        if not g:
            g = models.Genre(name=name, description=g_data.get("description"))
            db.add(g)
            db.flush()
        genres_map[name] = g.id

    stations_to_add = []
    for idx, st_data in enumerate(data.get("stations", []), start=1):
        st = dict(st_data)
        genre_name = st.pop("genre", None)
        genre_id = genres_map.get(genre_name) if genre_name else None

        if "metadata_url" not in st or not st["metadata_url"]:
            st["metadata_url"] = f"/stations/{idx}/metadata"

        station = models.Station(genre_id=genre_id, **st)
        stations_to_add.append(station)

    if stations_to_add:
        db.add_all(stations_to_add)
        db.commit()


@app.get("/stations", response_model=list[schemas.Station])
def list_stations(db: Session = Depends(get_db)):
    stations = db.scalars(select(models.Station).options(joinedload(models.Station.genre))).all()
    if not stations:
        _seed_initial_data(db)
        stations = db.scalars(select(models.Station).options(joinedload(models.Station.genre))).all()
    return stations


@app.post("/stations", response_model=schemas.Station, status_code=201)
def create_station(payload: schemas.StationCreate, db: Session = Depends(get_db)):
    station = models.Station(**payload.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@app.get("/stations/{station_id}", response_model=schemas.Station)
def get_station(station_id: int, db: Session = Depends(get_db)):
    station = db.scalar(
        select(models.Station).where(models.Station.id == station_id).options(joinedload(models.Station.genre))
    )
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


def _get_or_create_song(
    db: Session, artist: str, title: str, cover_image: str | None = None
) -> models.Song:
    song = db.scalar(
        select(models.Song).where(models.Song.artist == artist, models.Song.title == title)
    )
    if song is None:
        song = models.Song(artist=artist, title=title, cover_image=cover_image)
        db.add(song)
        db.commit()
        db.refresh(song)
    elif song.cover_image is None and cover_image is not None:
        song.cover_image = cover_image
        db.commit()
    return song


def _rating_summary(db: Session, song: models.Song, listener_id: str | None) -> schemas.SongRatingSummary:
    thumbs_up = db.scalar(
        select(func.count()).select_from(models.SongRating).where(
            models.SongRating.song_id == song.id, models.SongRating.rating == "up"
        )
    )
    thumbs_down = db.scalar(
        select(func.count()).select_from(models.SongRating).where(
            models.SongRating.song_id == song.id, models.SongRating.rating == "down"
        )
    )
    user_rating = None
    if listener_id:
        existing = db.scalar(
            select(models.SongRating).where(
                models.SongRating.song_id == song.id,
                models.SongRating.listener_id == listener_id,
            )
        )
        user_rating = existing.rating if existing else None
    return schemas.SongRatingSummary(
        artist=song.artist,
        title=song.title,
        thumbs_up=thumbs_up or 0,
        thumbs_down=thumbs_down or 0,
        user_rating=user_rating,
    )


@app.get("/songs/rating", response_model=schemas.SongRatingSummary)
def get_song_rating(
    artist: str, title: str, listener_id: str | None = None, db: Session = Depends(get_db)
):
    song = _get_or_create_song(db, artist, title)
    return _rating_summary(db, song, listener_id)


@app.post("/songs/rating", response_model=schemas.SongRatingSummary, status_code=201)
def rate_song(payload: schemas.SongRatingCreate, db: Session = Depends(get_db)):
    song = _get_or_create_song(db, payload.artist, payload.title, payload.cover_image)

    existing = db.scalar(
        select(models.SongRating).where(
            models.SongRating.song_id == song.id,
            models.SongRating.listener_id == payload.listener_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already rated this song")

    db.add(
        models.SongRating(
            song_id=song.id, listener_id=payload.listener_id, rating=payload.rating
        )
    )
    db.commit()

    return _rating_summary(db, song, payload.listener_id)


@app.get("/songs/disliked", response_model=schemas.DislikedSongsPage)
def list_disliked_songs(
    listener_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if page_size is None:
        page_size = settings.disliked_songs_page_size

    base_query = (
        select(
            models.Song.artist,
            models.Song.title,
            models.Song.cover_image,
            models.SongRating.created_at,
        )
        .join(models.SongRating, models.SongRating.song_id == models.Song.id)
        .where(models.SongRating.listener_id == listener_id, models.SongRating.rating == "down")
    )

    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

    rows = db.execute(
        base_query.order_by(models.SongRating.created_at.desc(), models.SongRating.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()

    return schemas.DislikedSongsPage(
        items=[
            schemas.DislikedSong(artist=artist, title=title, rated_at=created_at, cover_image=cover_image)
            for artist, title, cover_image, created_at in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
