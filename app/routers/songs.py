from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas
from app.config import settings
from app.repositories.deps import get_song_repository
from app.repositories.songs import SongRepository

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/rating", response_model=schemas.SongRatingSummary)
def get_song_rating(
    artist: str,
    title: str,
    listener_id: str | None = None,
    repo: SongRepository = Depends(get_song_repository),
):
    song = repo.get_or_create(artist, title)
    return repo.get_rating_summary(song, listener_id)


@router.post("/rating", response_model=schemas.SongRatingSummary, status_code=201)
def rate_song(
    payload: schemas.SongRatingCreate, repo: SongRepository = Depends(get_song_repository)
):
    song = repo.get_or_create(payload.artist, payload.title, payload.cover_image)

    existing = repo.get_existing_rating(song.id, payload.listener_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already rated this song")

    repo.rate_song(song.id, payload.listener_id, payload.rating)
    return repo.get_rating_summary(song, payload.listener_id)


@router.get("/disliked", response_model=schemas.DislikedSongsPage)
def list_disliked_songs(
    listener_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=None, ge=1, le=100),
    repo: SongRepository = Depends(get_song_repository),
):
    if page_size is None:
        page_size = settings.disliked_songs_page_size

    rows, total = repo.get_disliked_songs(listener_id, page, page_size)

    return schemas.DislikedSongsPage(
        items=[
            schemas.DislikedSong(artist=artist, title=title, rated_at=created_at, cover_image=cover_image)
            for artist, title, cover_image, created_at in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
