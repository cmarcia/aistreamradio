def test_get_rating_creates_song_with_zero_totals(client):
    res = client.get("/songs/rating", params={"artist": "Test", "title": "Song", "listener_id": "u1"})
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "artist": "Test",
        "title": "Song",
        "thumbs_up": 0,
        "thumbs_down": 0,
        "user_rating": None,
    }


def test_rate_song_up_increments_totals(client):
    res = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "up"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["thumbs_up"] == 1
    assert body["thumbs_down"] == 0
    assert body["user_rating"] == "up"


def test_rate_song_down_increments_totals(client):
    res = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "down"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["thumbs_up"] == 0
    assert body["thumbs_down"] == 1
    assert body["user_rating"] == "down"


def test_multiple_users_ratings_aggregate(client):
    client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "up"},
    )
    client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u2", "rating": "up"},
    )
    res = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u3", "rating": "down"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["thumbs_up"] == 2
    assert body["thumbs_down"] == 1


def test_cannot_rate_same_song_twice(client):
    first = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "up"},
    )
    assert first.status_code == 201

    second = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "down"},
    )
    assert second.status_code == 409

    # totals must be unaffected by the rejected second vote
    res = client.get("/songs/rating", params={"artist": "Test", "title": "Song", "listener_id": "u1"})
    body = res.json()
    assert body["thumbs_up"] == 1
    assert body["thumbs_down"] == 0
    assert body["user_rating"] == "up"


def test_ratings_are_scoped_per_song(client):
    client.post(
        "/songs/rating",
        json={"artist": "Artist A", "title": "Song A", "listener_id": "u1", "rating": "up"},
    )
    client.post(
        "/songs/rating",
        json={"artist": "Artist B", "title": "Song B", "listener_id": "u1", "rating": "down"},
    )

    res_a = client.get(
        "/songs/rating", params={"artist": "Artist A", "title": "Song A", "listener_id": "u1"}
    ).json()
    res_b = client.get(
        "/songs/rating", params={"artist": "Artist B", "title": "Song B", "listener_id": "u1"}
    ).json()

    assert res_a["thumbs_up"] == 1
    assert res_a["thumbs_down"] == 0
    assert res_b["thumbs_up"] == 0
    assert res_b["thumbs_down"] == 1


def test_invalid_rating_value_rejected(client):
    res = client.post(
        "/songs/rating",
        json={"artist": "Test", "title": "Song", "listener_id": "u1", "rating": "sideways"},
    )
    assert res.status_code == 422
