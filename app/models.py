from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    stations: Mapped[list["Station"]] = relationship("Station", back_populates="genre")


class Station(Base):
    __tablename__ = "stations"

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


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (UniqueConstraint("artist", "title", name="uq_song_artist_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True)


class SongRating(Base):
    __tablename__ = "song_ratings"
    __table_args__ = (
        UniqueConstraint("song_id", "listener_id", name="uq_rating_song_listener"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False, index=True)
    listener_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String, nullable=False)  # "up" or "down"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
