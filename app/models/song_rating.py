from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.utilities.database import Base


class SongRating(Base):
    __tablename__ = "song_ratings"
    __table_args__ = (
        UniqueConstraint("song_id", "listener_id", name="uq_rating_song_listener"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    listener_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String, nullable=False)  # "up" or "down"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
