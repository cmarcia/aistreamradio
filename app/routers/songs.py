from fastapi import APIRouter, Depends, HTTPException, Query, status


from app import models, schemas
from app.config import settings
from app.repositories.deps import get_song_repository
from app.repositories.songs import SongRepository
from app.utilities.auth import get_optional_user

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/rating", response_model=schemas.SongRatingSummary)
def get_song_rating(
    artist: str,
    title: str,
    listener_id: str | None = None,
    current_user: models.User | None = Depends(get_optional_user),
    repo: SongRepository = Depends(get_song_repository),
):
    song = repo.get_or_create(artist, title)
    user_id = current_user.id if current_user else None
    effective_listener_id = user_id or listener_id
    return repo.get_rating_summary(song, listener_id=effective_listener_id, user_id=user_id)


@router.post("/rating", response_model=schemas.SongRatingSummary, status_code=201)
def rate_song(
    payload: schemas.SongRatingCreate,
    current_user: models.User | None = Depends(get_optional_user),
    repo: SongRepository = Depends(get_song_repository),
):
    song = repo.get_or_create(payload.artist, payload.title, payload.cover_image)

    user_id = current_user.id if current_user else None
    effective_listener_id = user_id or payload.listener_id
    if not effective_listener_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="listener_id or authenticated user session is required.",
        )

    existing = repo.get_existing_rating(song.id, effective_listener_id, user_id=user_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already rated this song")

    repo.rate_song(song.id, effective_listener_id, payload.rating, user_id=user_id)
    return repo.get_rating_summary(song, listener_id=effective_listener_id, user_id=user_id)



@router.get("/disliked", response_model=schemas.DislikedSongsPage)
def list_disliked_songs(
    listener_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=None, ge=1, le=100),
    current_user: models.User | None = Depends(get_optional_user),
    repo: SongRepository = Depends(get_song_repository),
):
    user_id = current_user.id if current_user else None
    if not user_id and not listener_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="listener_id query parameter or authenticated session is required.",
        )
    effective_listener_id = user_id or listener_id or ""


    if page_size is None:
        page_size = settings.disliked_songs_page_size

    rows, total = repo.get_disliked_songs(effective_listener_id, page, page_size, user_id=user_id)

    return schemas.DislikedSongsPage(
        items=[
            schemas.DislikedSong(artist=artist, title=title, rated_at=created_at, cover_image=cover_image)
            for artist, title, cover_image, created_at in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )

