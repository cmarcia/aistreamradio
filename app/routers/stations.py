import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.icy import fetch_icy_metadata

router = APIRouter(prefix="/stations", tags=["stations"])

STATIC_DIR = Path(__file__).parent.parent / "static"
COVER_TEMPLATE_PATH = STATIC_DIR / "Images" / "station-cover-template.svg"
INITIAL_STATIONS_PATH = Path(__file__).parent.parent.parent / "data" / "initial_stations.json"


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


@router.get("", response_model=list[schemas.Station])
def list_stations(db: Session = Depends(get_db)):
    stations = db.scalars(select(models.Station).options(joinedload(models.Station.genre))).all()
    if not stations:
        _seed_initial_data(db)
        stations = db.scalars(select(models.Station).options(joinedload(models.Station.genre))).all()
    return stations


@router.post("", response_model=schemas.Station, status_code=201)
def create_station(payload: schemas.StationCreate, db: Session = Depends(get_db)):
    station = models.Station(**payload.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.get("/{station_id}", response_model=schemas.Station)
def get_station(station_id: int, db: Session = Depends(get_db)):
    station = db.scalar(
        select(models.Station).where(models.Station.id == station_id).options(joinedload(models.Station.genre))
    )
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/{station_id}/stream")
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


@router.get("/{station_id}/metadata")
async def get_station_metadata(station_id: int, db: Session = Depends(get_db)):
    current_year = str(datetime.now(timezone.utc).year)
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
            "date": current_year,
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
        "date": station.date or current_year,
        "bit_depth": station.bit_depth or 16,
        "sample_rate": station.sample_rate or 44100,
        "cover_url": cover_url,
    }


@router.get("/{station_id}/cover")
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
