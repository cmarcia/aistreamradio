import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.repositories.songs import SongRepository


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_get_or_create_song_creates_once(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    assert song.id is not None

    same_song = repo.get_or_create("Artist", "Title")
    assert same_song.id == song.id

    count = db_session.query(models.Song).count()
    assert count == 1


def test_get_or_create_song_distinguishes_by_artist_and_title(db_session):
    repo = SongRepository(db_session)
    song_a = repo.get_or_create("Artist A", "Same Title")
    song_b = repo.get_or_create("Artist B", "Same Title")
    assert song_a.id != song_b.id


def test_rating_summary_with_no_ratings(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    summary = repo.get_rating_summary(song, listener_id=None)
    assert summary.thumbs_up == 0
    assert summary.thumbs_down == 0
    assert summary.user_rating is None


def test_rating_summary_counts_and_user_rating(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    db_session.add(models.SongRating(song_id=song.id, listener_id="u1", rating="up"))
    db_session.add(models.SongRating(song_id=song.id, listener_id="u2", rating="down"))
    db_session.add(models.SongRating(song_id=song.id, listener_id="u3", rating="down"))
    db_session.commit()

    summary = repo.get_rating_summary(song, listener_id="u2")
    assert summary.thumbs_up == 1
    assert summary.thumbs_down == 2
    assert summary.user_rating == "down"


def test_rating_summary_unknown_listener_has_no_user_rating(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    db_session.add(models.SongRating(song_id=song.id, listener_id="u1", rating="up"))
    db_session.commit()

    summary = repo.get_rating_summary(song, listener_id="unknown-user")
    assert summary.user_rating is None


def test_get_or_create_song_stores_cover_image_on_creation(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title", cover_image="data:image/jpeg;base64,AAAA")
    assert song.cover_image == "data:image/jpeg;base64,AAAA"


def test_get_or_create_song_backfills_missing_cover_image(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    assert song.cover_image is None

    same_song = repo.get_or_create(
        "Artist", "Title", cover_image="data:image/jpeg;base64,LATER"
    )
    assert same_song.id == song.id
    assert same_song.cover_image == "data:image/jpeg;base64,LATER"


def test_get_or_create_song_does_not_overwrite_existing_cover_image(db_session):
    repo = SongRepository(db_session)
    repo.get_or_create("Artist", "Title", cover_image="data:image/jpeg;base64,FIRST")
    song = repo.get_or_create(
        "Artist", "Title", cover_image="data:image/jpeg;base64,SECOND"
    )
    assert song.cover_image == "data:image/jpeg;base64,FIRST"


def test_duplicate_rating_violates_db_unique_constraint(db_session):
    repo = SongRepository(db_session)
    song = repo.get_or_create("Artist", "Title")
    db_session.add(models.SongRating(song_id=song.id, listener_id="u1", rating="up"))
    db_session.commit()

    db_session.add(models.SongRating(song_id=song.id, listener_id="u1", rating="down"))
    with pytest.raises(IntegrityError):
        db_session.commit()
