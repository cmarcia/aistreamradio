from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utilities.database import Base
from app.models.song_artist import song_artists

if TYPE_CHECKING:
    from app.models.artist import Artist


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True)

    artists: Mapped[list[Artist]] = relationship(
        "Artist", secondary=song_artists, back_populates="songs"
    )

    @property
    def artist(self) -> str:
        """Returns comma-separated names of linked artists for backward compatibility."""
        if hasattr(self, "artists") and self.artists:
            return ", ".join(a.name for a in self.artists)
        return ""
