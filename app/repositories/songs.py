from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas


class SongRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(
        self, artist: str, title: str, cover_image: str | None = None
    ) -> models.Song:
        song = self.db.scalar(
            select(models.Song).where(models.Song.artist == artist, models.Song.title == title)
        )
        if song is None:
            song = models.Song(artist=artist, title=title, cover_image=cover_image)
            self.db.add(song)
            self.db.commit()
            self.db.refresh(song)
        elif song.cover_image is None and cover_image is not None:
            song.cover_image = cover_image
            self.db.commit()
            self.db.refresh(song)
        return song

    def get_existing_rating(self, song_id: int, listener_id: str) -> models.SongRating | None:
        return self.db.scalar(
            select(models.SongRating).where(
                models.SongRating.song_id == song_id,
                models.SongRating.listener_id == listener_id,
            )
        )

    def rate_song(self, song_id: int, listener_id: str, rating: str) -> models.SongRating:
        rating_obj = models.SongRating(song_id=song_id, listener_id=listener_id, rating=rating)
        self.db.add(rating_obj)
        self.db.commit()
        self.db.refresh(rating_obj)
        return rating_obj

    def get_rating_summary(
        self, song: models.Song, listener_id: str | None = None
    ) -> schemas.SongRatingSummary:
        thumbs_up = self.db.scalar(
            select(func.count()).select_from(models.SongRating).where(
                models.SongRating.song_id == song.id, models.SongRating.rating == "up"
            )
        )
        thumbs_down = self.db.scalar(
            select(func.count()).select_from(models.SongRating).where(
                models.SongRating.song_id == song.id, models.SongRating.rating == "down"
            )
        )
        user_rating = None
        if listener_id:
            existing = self.get_existing_rating(song.id, listener_id)
            user_rating = existing.rating if existing else None

        return schemas.SongRatingSummary(
            artist=song.artist,
            title=song.title,
            thumbs_up=thumbs_up or 0,
            thumbs_down=thumbs_down or 0,
            user_rating=user_rating,
        )

    def get_disliked_songs(
        self, listener_id: str, page: int, page_size: int
    ) -> tuple[Sequence[tuple], int]:
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

        total = self.db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

        rows = self.db.execute(
            base_query.order_by(models.SongRating.created_at.desc(), models.SongRating.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()

        return rows, total
