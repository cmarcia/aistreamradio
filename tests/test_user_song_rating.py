import pytest
from app import models
from app.repositories.songs import SongRepository
from app.repositories.users import UserRepository
from app.utilities.auth import create_access_token


def test_authenticated_user_rating_stores_user_id(client, db_session):
    user_repo = UserRepository(db_session)
    user = user_repo.create_user_with_password("listener1@cyber.io", "Pass12345!")
    token = create_access_token({"sub": user.id, "email": user.email})

    # Set auth cookie
    client.cookies.set("app_session", token)

    # Rate song
    res = client.post(
        "/songs/rating",
        json={"artist": "Synth Artist", "title": "Track 01", "rating": "up"},
    )
    assert res.status_code == 201
    assert res.json()["user_rating"] == "up"

    # Verify DB record has user_id set to user.id
    song_repo = SongRepository(db_session)
    song = song_repo.get_or_create("Synth Artist", "Track 01")
    rating = song_repo.get_existing_rating(song.id, listener_id=user.id, user_id=user.id)
    assert rating is not None
    assert rating.user_id == user.id
    assert rating.listener_id == user.id


def test_each_user_has_own_ranking_and_ratings(client, db_session):
    user_repo = UserRepository(db_session)
    user_a = user_repo.create_user_with_password("usera@cyber.io", "Pass12345!")
    user_b = user_repo.create_user_with_password("userb@cyber.io", "Pass12345!")

    token_a = create_access_token({"sub": user_a.id, "email": user_a.email})
    token_b = create_access_token({"sub": user_b.id, "email": user_b.email})

    # User A rates Song "up"
    client.cookies.set("app_session", token_a)
    res_a = client.post(
        "/songs/rating",
        json={"artist": "Vector Pulse", "title": "Cyber Drift", "rating": "up"},
    )
    assert res_a.status_code == 201
    assert res_a.json()["user_rating"] == "up"

    # User B rates same Song "down"
    client.cookies.set("app_session", token_b)
    res_b = client.post(
        "/songs/rating",
        json={"artist": "Vector Pulse", "title": "Cyber Drift", "rating": "down"},
    )
    assert res_b.status_code == 201
    assert res_b.json()["user_rating"] == "down"
    assert res_b.json()["thumbs_up"] == 1
    assert res_b.json()["thumbs_down"] == 1

    # Check disliked list for User B
    disliked_b = client.get("/songs/disliked").json()
    assert len(disliked_b["items"]) == 1
    assert disliked_b["items"][0]["title"] == "Cyber Drift"

    # Check disliked list for User A (should be empty)
    client.cookies.set("app_session", token_a)
    disliked_a = client.get("/songs/disliked").json()
    assert len(disliked_a["items"]) == 0
