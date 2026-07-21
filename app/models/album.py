from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.artist import Artist


class Album(Base):
    __tablename__ = "albums"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"), nullable=True, index=True)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    artist: Mapped[Artist | None] = relationship("Artist", back_populates="albums")

    @property
    def album_url(self) -> str | None:
        """Alias for cover_url to support accessing the cover art URL as album_url."""
        return self.cover_url
