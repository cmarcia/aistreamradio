from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.genre import Genre


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    genre_id: Mapped[int | None] = mapped_column(ForeignKey("genres.id"), nullable=True, index=True)
    stream_url: Mapped[str] = mapped_column(
        String, nullable=False, default="https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8"
    )
    metadata_url: Mapped[str | None] = mapped_column(
        String, nullable=True, default="https://d3d4yli4hf5bmh.cloudfront.net/metadata.json"
    )
    current_artist: Mapped[str | None] = mapped_column(String, nullable=True)
    current_title: Mapped[str | None] = mapped_column(String, nullable=True)
    current_album: Mapped[str | None] = mapped_column(String, nullable=True)
    has_track_info: Mapped[bool] = mapped_column(Integer, nullable=False, default=True)
    date: Mapped[str | None] = mapped_column(
        String, nullable=True, default=lambda: str(datetime.now(timezone.utc).year)
    )
    bit_depth: Mapped[int | None] = mapped_column(Integer, nullable=True, default=16)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True, default=44100)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String, nullable=True, default="#00f3ff")
    secondary_color: Mapped[str | None] = mapped_column(String, nullable=True, default="#3b82f6")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    genre: Mapped[Genre | None] = relationship("Genre", back_populates="stations")
