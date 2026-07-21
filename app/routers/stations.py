import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import schemas
from app.config import settings
from app.icy import fetch_icy_metadata
from app.logging_config import logger
from app.repositories.deps import get_station_repository
from app.repositories.stations import StationRepository

router = APIRouter(prefix="/stations", tags=["stations"])

STATIC_DIR = Path(__file__).parent.parent / "static"
COVER_TEMPLATE_PATH = STATIC_DIR / "Images" / "station-cover-template.svg"


async def fetch_itunes_cover_art(artist: str, title: str, timeout: float = 2.5) -> str | None:
    if not artist or not title:
        return None
    clean_title = title.split("(")[0].strip()
    query = f"{artist} {clean_title}"
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results and "artworkUrl100" in results[0]:
                    return results[0]["artworkUrl100"].replace("100x100bb", "600x600bb")
    except Exception as exc:
        logger.debug(f"iTunes cover art search error for '{artist} - {title}': {exc}")
    return None


@router.get("", response_model=list[schemas.Station])
def list_stations(repo: StationRepository = Depends(get_station_repository)):
    return repo.get_all()


@router.post("", response_model=schemas.Station, status_code=201)
def create_station(
    payload: schemas.StationCreate, repo: StationRepository = Depends(get_station_repository)
):
    return repo.create(payload)


@router.get("/{station_id}", response_model=schemas.Station)
def get_station(station_id: int, repo: StationRepository = Depends(get_station_repository)):
    station = repo.get_by_id(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/{station_id}/stream")
async def get_station_stream(
    station_id: int, repo: StationRepository = Depends(get_station_repository)
):
    station = repo.get_by_id(station_id)
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
async def get_station_metadata(
    station_id: int, repo: StationRepository = Depends(get_station_repository)
):
    current_year = str(datetime.now(timezone.utc).year)
    station = repo.get_by_id(station_id)

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

    # 1. Attempt live ICY stream metadata probe
    has_live_info = False
    if station.stream_url and station.stream_url.startswith("http"):
        live_meta = await fetch_icy_metadata(station.stream_url, timeout=3.0)
        if live_meta and live_meta.get("title"):
            station = repo.update_live_metadata(
                station=station,
                artist=live_meta["artist"],
                title=live_meta["title"],
                cover_url=live_meta.get("cover_url"),
            )
            has_live_info = True

    # 2. If ICY probe yields no title, check for HTTP JSON metadata feed
    if not has_live_info and station.metadata_url and station.metadata_url.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                resp = await client.get(station.metadata_url)
                if resp.status_code == 200:
                    meta_json = resp.json()
                    if meta_json.get("title"):
                        station.current_artist = meta_json.get("artist") or station.name
                        station.current_title = meta_json.get("title")
                        station.current_album = meta_json.get("album") or station.current_album
                        station.has_track_info = True
                        if meta_json.get("date"):
                            station.date = str(meta_json.get("date"))
                        if meta_json.get("bit_depth"):
                            station.bit_depth = int(meta_json.get("bit_depth"))
                        if meta_json.get("sample_rate"):
                            station.sample_rate = int(meta_json.get("sample_rate"))
                        if meta_json.get("cover_url"):
                            station.cover_url = meta_json.get("cover_url")
                        repo.db.commit()
                        repo.db.refresh(station)
                        has_live_info = True
                        logger.info(
                            f"Fetched HTTP JSON metadata for '{station.name}': '{station.current_artist} - {station.current_title}'"
                        )
        except Exception as exc:
            logger.warning(f"HTTP JSON metadata probe failed for {station.metadata_url}: {exc}")

    # 3. If track info exists but cover_url is missing, fetch album artwork dynamically
    if (
        station.has_track_info
        and station.current_artist
        and station.current_title
        and not station.cover_url
    ):
        art_url = await fetch_itunes_cover_art(station.current_artist, station.current_title)
        if art_url:
            station.cover_url = art_url
            repo.db.commit()
            repo.db.refresh(station)
            logger.info(f"Dynamically retrieved album cover art for '{station.current_artist} - {station.current_title}': {art_url}")

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
def get_station_cover(
    station_id: int, repo: StationRepository = Depends(get_station_repository)
):
    station = repo.get_by_id(station_id)
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
