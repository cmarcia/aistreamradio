import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


@router.get("/cover-proxy")
async def cover_proxy(url: str = Query(...)):
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Cover image not found")

            media_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=media_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=86400",
                },
            )
    except Exception as exc:
        logger.warning(f"Error proxying cover image URL '{url}': {exc}")
        raise HTTPException(status_code=502, detail="Failed to fetch remote cover image")


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


def parse_external_station_metadata(data: dict) -> dict | None:
    if not isinstance(data, dict):
        return None

    if data.get("title"):
        return {
            "artist": data.get("artist"),
            "title": data.get("title"),
            "album": data.get("album"),
            "cover_url": data.get("cover_url") or data.get("albumArt"),
            "date": data.get("date"),
        }

    songs = data.get("songs")
    if isinstance(songs, list) and len(songs) > 0 and isinstance(songs[0], dict):
        s = songs[0]
        if s.get("title"):
            return {
                "artist": s.get("artist"),
                "title": s.get("title"),
                "album": s.get("album"),
                "cover_url": s.get("albumArt"),
                "date": s.get("date"),
            }

    item = data.get("current_playlist_item")
    if isinstance(item, dict):
        cat = item.get("catalog_entry") if isinstance(item.get("catalog_entry"), dict) else {}
        comp = cat.get("composer") if isinstance(cat.get("composer"), dict) else {}
        title = cat.get("title") or item.get("title")
        artist = comp.get("name") or cat.get("artist")
        if title:
            return {
                "artist": artist,
                "title": title,
                "album": cat.get("album"),
                "cover_url": cat.get("artwork_url"),
                "date": None,
            }

    show = data.get("current_show")
    if isinstance(show, dict) and show.get("title"):
        img = show.get("fullImage")
        cover_url = img.get("url") if isinstance(img, dict) else None
        return {
            "artist": show.get("title"),
            "title": "Live Broadcast",
            "album": "Radio Broadcast",
            "cover_url": cover_url,
            "date": None,
        }

    return None


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
                resp = await client.get(station.metadata_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    parsed = parse_external_station_metadata(resp.json())
                    if parsed and parsed.get("title"):
                        new_title = parsed["title"]
                        new_artist = parsed.get("artist") or station.name
                        if station.current_title != new_title or station.current_artist != new_artist:
                            station.cover_url = parsed.get("cover_url")

                        station.current_artist = new_artist
                        station.current_title = new_title
                        station.current_album = parsed.get("album") or station.current_album
                        station.has_track_info = True
                        if parsed.get("date"):
                            station.date = str(parsed.get("date"))
                        if parsed.get("cover_url"):
                            station.cover_url = parsed.get("cover_url")
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
            logger.info(
                f"Dynamically retrieved album cover art for '{station.current_artist} - {station.current_title}': {art_url}"
            )

    genre_name = station.genre.name if station.genre else "Live Music"
    raw_cover_url = station.cover_url or f"/stations/{station.id}/cover"
    if raw_cover_url.startswith("http://") or raw_cover_url.startswith("https://"):
        cover_url = f"/stations/cover-proxy?url={urllib.parse.quote(raw_cover_url)}"
    else:
        cover_url = raw_cover_url

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
