from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/songs", tags=["songs"])


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


@router.get("/rating", response_model=schemas.SongRatingSummary)
def get_song_rating(
    artist: str, title: str, listener_id: str | None = None, db: Session = Depends(get_db)
):
    song = _get_or_create_song(db, artist, title)
    return _rating_summary(db, song, listener_id)


@router.post("/rating", response_model=schemas.SongRatingSummary, status_code=201)
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


@router.get("/disliked", response_model=schemas.DislikedSongsPage)
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
