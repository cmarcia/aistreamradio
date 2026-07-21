from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.song_artist import song_artists

if TYPE_CHECKING:
    from app.models.album import Album
    from app.models.song import Song


class Artist(Base):
    __tablename__ = "artists"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    albums: Mapped[list[Album]] = relationship("Album", back_populates="artist")
    songs: Mapped[list[Song]] = relationship(
        "Song", secondary=song_artists, back_populates="artists"
    )
