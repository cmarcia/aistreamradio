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


@app.get("/stations", response_model=list[schemas.Station])
def list_stations(db: Session = Depends(get_db)):
    stations = db.scalars(select(models.Station).options(joinedload(models.Station.genre))).all()
    if not stations:
        genres_map = {}
        default_genres_data = [
            ("Pop / Mainstream Hits", "Popular music charts and top radio hits"),
            ("News / Talk / Pop Music", "News broadcasts, talk radio, and music"),
            ("Indie / Alternative / Post-Rock", "Independent, alternative, and experimental music"),
            ("Hebrew Pop / Mizrahi / Middle Eastern", "Mizrahi, Hebrew pop, and regional music"),
            ("Hasidic / Cantorial / Talk", "Hasidic songs, cantorial music, and talk"),
            ("Heavy Metal / Thrash / Hard Rock", "Heavy metal, thrash, and hard rock music"),
            ("Classic Rock / 70s & 80s Rock", "Classic rock, 70s anthems, and 80s rock hits"),
            ("Classical Music", "Classical, symphonic, orchestral, and opera music"),
        ]
        for name, desc in default_genres_data:
            g = db.scalar(select(models.Genre).where(models.Genre.name == name))
            if not g:
                g = models.Genre(name=name, description=desc)
                db.add(g)
                db.flush()
            genres_map[name] = g.id

        default_stations = [
            models.Station(
                name="Galglatz (גלגלצ)",
                frequency="91.8 FM",
                genre_id=genres_map.get("Pop / Mainstream Hits"),
                stream_url="https://glzwizzlv.bynetcdn.com/glglz_mp3",
                metadata_url="/stations/1/metadata",
                current_artist="Galglatz (גלגלצ)",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#00f3ff",
                secondary_color="#3b82f6",
                cover_url=None,
            ),
            models.Station(
                name="Galei Tzahal (גלי צה\"ל)",
                frequency="104.0 FM",
                genre_id=genres_map.get("News / Talk / Pop Music"),
                stream_url="https://glzwizzlv.bynetcdn.com/glz_mp3?awCollectionId=misc&awEpisodeId=glz",
                metadata_url="/stations/2/metadata",
                current_artist="Galei Tzahal (גלי צה\"ל)",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#10b981",
                secondary_color="#047857",
                cover_url=None,
            ),
            models.Station(
                name="Hakatze / The Edge (הקצה)",
                frequency="Online",
                genre_id=genres_map.get("Indie / Alternative / Post-Rock"),
                stream_url="http://kzradio.mediacast.co.il/kzradio_live/kzradio/icecast.audio",
                metadata_url="/stations/3/metadata",
                current_artist="Hakatze Radio (הקצה)",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                primary_color="#ff007f",
                secondary_color="#9d4edd",
                cover_url=None,
            ),
            models.Station(
                name="Galei Israel (גלי ישראל)",
                frequency="94.0 FM",
                genre_id=genres_map.get("Hebrew Pop / Mizrahi / Middle Eastern"),
                stream_url="https://cdn.cybercdn.live/Galei_Israel/Live/icecast.audio",
                metadata_url="/stations/4/metadata",
                current_artist="Galei Israel (גלי ישראל)",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#ff9e00",
                secondary_color="#d97706",
                cover_url=None,
            ),
            models.Station(
                name="Kol Chai (קול חי)",
                frequency="93.0 FM",
                genre_id=genres_map.get("Hasidic / Cantorial / Talk"),
                stream_url="https://media2.93fm.co.il/live-new",
                metadata_url="/stations/5/metadata",
                current_artist="Kol Chai (קול חי)",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#8b5cf6",
                secondary_color="#4c1d95",
                cover_url=None,
            ),
            models.Station(
                name="Metal Detector",
                frequency="Online",
                genre_id=genres_map.get("Heavy Metal / Thrash / Hard Rock"),
                stream_url="https://ice1.somafm.com/metal-128-mp3",
                metadata_url="/stations/6/metadata",
                current_artist="Metal Detector",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                primary_color="#ff0033",
                secondary_color="#800000",
                cover_url=None,
            ),
            models.Station(
                name="Classic Rock Vault",
                frequency="Online",
                genre_id=genres_map.get("Classic Rock / 70s & 80s Rock"),
                stream_url="https://ice1.somafm.com/defcon-128-mp3",
                metadata_url="/stations/7/metadata",
                current_artist="Classic Rock Vault",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#ffaa00",
                secondary_color="#7a4d00",
                cover_url=None,
            ),
            models.Station(
                name="WQXR 105.9 FM Classical",
                frequency="105.9 FM",
                genre_id=genres_map.get("Classical Music"),
                stream_url="https://stream.wqxr.org/wqxr",
                metadata_url="/stations/8/metadata",
                current_artist="WQXR 105.9 FM Classical",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                primary_color="#00c8ff",
                secondary_color="#4f46e5",
                cover_url=None,
            ),
            models.Station(
                name="Klassik Radio Symphony",
                frequency="Online",
                genre_id=genres_map.get("Classical Music"),
                stream_url="https://klassik-high.rautemusik.fm/?ref=radiobrowser",
                metadata_url="/stations/9/metadata",
                current_artist="Klassik Radio Symphony",
                current_title=None,
                current_album="Live Broadcast",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                primary_color="#eab308",
                secondary_color="#854d0e",
                cover_url=None,
            ),
        ]
        db.add_all(default_stations)
        db.commit()
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
