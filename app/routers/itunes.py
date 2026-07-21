from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services.itunes import ITunesService

router = APIRouter(prefix="/itunes", tags=["itunes"])


@router.get("/search", response_model=schemas.ITunesSearchResult)
async def search_itunes_endpoint(
    title: str = Query(..., description="Song title"),
    artist: str = Query(..., description="Artist name"),
    release_date: str | None = Query(None, description="Optional release date or year"),
    album: str | None = Query(None, description="Optional album name"),
    db: Session = Depends(get_db),
):
    """
    Query iTunes Search API for song, artist, album, cover art URL, and release date/year.
    Persists Artist and Album records into the database.
    """
    service = ITunesService(db)
    result = await service.fetch_and_persist(
        title=title,
        artist=artist,
        release_date=release_date,
        album=album,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No information found on iTunes for the requested track",
        )
    return result
