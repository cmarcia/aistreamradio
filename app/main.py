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
async def get_station_stream(station_id: int):
    target_urls = {
        1: "https://glzwizzlv.bynetcdn.com/glglz_mp3",
        2: "https://glzwizzlv.bynetcdn.com/glz_mp3?awCollectionId=misc&awEpisodeId=glz",
        3: "http://kzradio.mediacast.co.il/kzradio_live/kzradio/icecast.audio",
        4: "https://cdn.cybercdn.live/Galei_Israel/Live/icecast.audio",
        5: "https://media2.93fm.co.il/live-new",
        6: "https://ice1.somafm.com/metal-128-mp3",
        7: "https://ice1.somafm.com/defcon-128-mp3",
        8: "https://stream.wqxr.org/wqxr",
        9: "https://klassik-high.rautemusik.fm/?ref=radiobrowser",
    }
    url = target_urls.get(station_id, target_urls[1])

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
def get_station_metadata(station_id: int, db: Session = Depends(get_db)):
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
            "cover_url": None,
        }

    genre_name = station.genre.name if station.genre else "Live Music"
    cover_url = station.cover_url or (f"/stations/{station.id}/cover" if station.has_track_info else None)

    return {
        "artist": station.current_artist or station.name,
        "title": station.current_title,
        "album": station.current_album or "Radio Broadcast",
        "genre": genre_name,
        "has_track_info": station.has_track_info,
        "date": station.date or "2026",
        "bit_depth": station.bit_depth or 16,
        "sample_rate": station.sample_rate or 44100,
        "cover_url": cover_url,
    }


@app.get("/stations/{station_id}/cover")
def get_station_cover(station_id: int):
    colors = {
        1: ("#00f3ff", "#3b82f6", "GALGLATZ", "91.8 FM • גלגלצ"),
        2: ("#10b981", "#047857", "GALEI TZAHAL", "104.0 FM • גלי צה\"ל"),
        3: ("#ff007f", "#9d4edd", "HAKATZE", "THE EDGE • הקצה"),
        4: ("#ff9e00", "#d97706", "GALEI ISRAEL", "94.0 FM • גלי ישראל"),
        5: ("#8b5cf6", "#4c1d95", "KOL CHAI", "93.0 FM • קול חי"),
        6: ("#ff0033", "#800000", "METAL DETECTOR", "HEAVY METAL / HARD ROCK"),
        7: ("#ffaa00", "#7a4d00", "CLASSIC ROCK", "CLASSIC ROCK / 70S & 80S"),
        8: ("#00c8ff", "#4f46e5", "WQXR CLASSICAL", "105.9 FM • CLASSICAL MUSIC"),
        9: ("#eab308", "#854d0e", "KLASSIK SYMPHONY", "CLASSICAL MUSIC"),
    }
    bg1, bg2, title, genre = colors.get(
        station_id, ("#00f3ff", "#9d4edd", f"STATION {station_id}", "RADIO STREAM")
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="{bg1}" stop-opacity="0.9"/>
          <stop offset="100%" stop-color="{bg2}" stop-opacity="0.95"/>
        </linearGradient>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect width="500" height="500" fill="#080b14"/>
      <rect width="500" height="500" fill="url(#g)"/>
      <rect width="500" height="500" fill="url(#grid)"/>
      <circle cx="250" cy="220" r="120" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
      <circle cx="250" cy="220" r="80" fill="none" stroke="{bg1}" stroke-width="4"/>
      <polygon points="230,190 280,220 230,250" fill="#ffffff"/>
      <text x="250" y="380" font-family="sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle" letter-spacing="2">{title}</text>
      <text x="250" y="420" font-family="sans-serif" font-size="16" font-weight="600" fill="{bg1}" text-anchor="middle" letter-spacing="1">{genre}</text>
    </svg>"""
    return Response(content=svg, media_type="image/svg+xml")


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
                stream_url="/stations/1/stream",
                metadata_url="/stations/1/metadata",
                current_artist="Galglatz (גלגלצ)",
                current_title="סופשבוע רגוע בגלגלצ",
                current_album="Galglatz Top Chart Hits",
                has_track_info=True,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url="/stations/1/cover",
            ),
            models.Station(
                name="Galei Tzahal (גלי צה\"ל)",
                frequency="104.0 FM",
                genre_id=genres_map.get("News / Talk / Pop Music"),
                stream_url="/stations/2/stream",
                metadata_url="/stations/2/metadata",
                current_artist="Galei Tzahal (גלי צה\"ל)",
                current_title="חדשות ומוזיקה",
                current_album="GLZ Live Broadcast",
                has_track_info=True,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url="/stations/2/cover",
            ),
            models.Station(
                name="Hakatze / The Edge (הקצה)",
                frequency="Online",
                genre_id=genres_map.get("Indie / Alternative / Post-Rock"),
                stream_url="/stations/3/stream",
                metadata_url="/stations/3/metadata",
                current_artist="Hakatze Radio (הקצה)",
                current_title="Indie & Alternative Session",
                current_album="Tel Aviv Independent",
                has_track_info=True,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                cover_url="/stations/3/cover",
            ),
            models.Station(
                name="Galei Israel (גלי ישראל)",
                frequency="94.0 FM",
                genre_id=genres_map.get("Hebrew Pop / Mizrahi / Middle Eastern"),
                stream_url="/stations/4/stream",
                metadata_url="/stations/4/metadata",
                current_artist="Galei Israel (גלי ישראל)",
                current_title="מוזיקה ותרבות",
                current_album="Regional Music Broadcast",
                has_track_info=True,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url="/stations/4/cover",
            ),
            models.Station(
                name="Kol Chai (קול חי)",
                frequency="93.0 FM",
                genre_id=genres_map.get("Hasidic / Cantorial / Talk"),
                stream_url="/stations/5/stream",
                metadata_url="/stations/5/metadata",
                current_artist="Kol Chai (קול חי)",
                current_title="מוזיקה יהודית ושידורים חיים",
                current_album="Kol Chai Radio",
                has_track_info=True,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url="/stations/5/cover",
            ),
            models.Station(
                name="Metal Detector",
                frequency="Online",
                genre_id=genres_map.get("Heavy Metal / Thrash / Hard Rock"),
                stream_url="/stations/6/stream",
                metadata_url="/stations/6/metadata",
                current_artist="Metal Detector Broadcast",
                current_title="Painkiller (Live Metal Feed)",
                current_album="Heavy Metal Anthems",
                has_track_info=True,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                cover_url="/stations/6/cover",
            ),
            models.Station(
                name="Classic Rock Vault",
                frequency="Online",
                genre_id=genres_map.get("Classic Rock / 70s & 80s Rock"),
                stream_url="/stations/7/stream",
                metadata_url="/stations/7/metadata",
                current_artist="Classic Rock Vault",
                current_title=None,
                current_album="70s & 80s Rock Classics",
                has_track_info=False,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url=None,
            ),
            models.Station(
                name="WQXR 105.9 FM Classical",
                frequency="105.9 FM",
                genre_id=genres_map.get("Classical Music"),
                stream_url="/stations/8/stream",
                metadata_url="/stations/8/metadata",
                current_artist="WQXR Classical NY",
                current_title="Symphony No. 5 in C minor, Op. 67 (Beethoven)",
                current_album="WQXR Philharmonic Broadcast",
                has_track_info=True,
                date="2026",
                bit_depth=24,
                sample_rate=48000,
                cover_url="/stations/8/cover",
            ),
            models.Station(
                name="Klassik Radio Symphony",
                frequency="Online",
                genre_id=genres_map.get("Classical Music"),
                stream_url="/stations/9/stream",
                metadata_url="/stations/9/metadata",
                current_artist="Klassik Radio Symphony",
                current_title="Four Seasons: Spring (Vivaldi)",
                current_album="Baroque & Classical Masterpieces",
                has_track_info=True,
                date="2026",
                bit_depth=16,
                sample_rate=44100,
                cover_url="/stations/9/cover",
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
