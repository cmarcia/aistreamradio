def test_disliked_songs_empty_for_new_listener(client):
    res = client.get("/songs/disliked", params={"listener_id": "u1"})
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


def test_disliked_songs_lists_only_downvotes(client):
    client.post(
        "/songs/rating",
        json={"artist": "Artist A", "title": "Song A", "listener_id": "u1", "rating": "up"},
    )
    client.post(
        "/songs/rating",
        json={"artist": "Artist B", "title": "Song B", "listener_id": "u1", "rating": "down"},
    )

    res = client.get("/songs/disliked", params={"listener_id": "u1"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["artist"] == "Artist B"
    assert body["items"][0]["title"] == "Song B"
    assert "rated_at" in body["items"][0]


def test_disliked_songs_scoped_per_listener(client):
    client.post(
        "/songs/rating",
        json={"artist": "Artist A", "title": "Song A", "listener_id": "u1", "rating": "down"},
    )
    client.post(
        "/songs/rating",
        json={"artist": "Artist B", "title": "Song B", "listener_id": "u2", "rating": "down"},
    )

    res_u1 = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    res_u2 = client.get("/songs/disliked", params={"listener_id": "u2"}).json()

    assert [s["title"] for s in res_u1["items"]] == ["Song A"]
    assert [s["title"] for s in res_u2["items"]] == ["Song B"]


def test_disliked_songs_ordered_most_recent_first(client):
    client.post(
        "/songs/rating",
        json={"artist": "Artist A", "title": "Song A", "listener_id": "u1", "rating": "down"},
    )
    client.post(
        "/songs/rating",
        json={"artist": "Artist B", "title": "Song B", "listener_id": "u1", "rating": "down"},
    )

    res = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    assert [s["title"] for s in res["items"]] == ["Song B", "Song A"]


def test_disliked_songs_requires_listener_id(client):
    res = client.get("/songs/disliked")
    assert res.status_code == 422


def test_disliked_songs_includes_cover_image_when_provided(client):
    client.post(
        "/songs/rating",
        json={
            "artist": "Artist A",
            "title": "Song A",
            "listener_id": "u1",
            "rating": "down",
            "cover_image": "data:image/jpeg;base64,AAAA",
        },
    )

    res = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    assert res["items"][0]["cover_image"] == "data:image/jpeg;base64,AAAA"


def test_disliked_songs_cover_image_defaults_to_none(client):
    client.post(
        "/songs/rating",
        json={"artist": "Artist A", "title": "Song A", "listener_id": "u1", "rating": "down"},
    )

    res = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    assert res["items"][0]["cover_image"] is None


def test_cover_image_not_overwritten_by_later_rating(client):
    client.post(
        "/songs/rating",
        json={
            "artist": "Artist A",
            "title": "Song A",
            "listener_id": "u1",
            "rating": "down",
            "cover_image": "data:image/jpeg;base64,FIRST",
        },
    )
    client.post(
        "/songs/rating",
        json={
            "artist": "Artist A",
            "title": "Song A",
            "listener_id": "u2",
            "rating": "down",
            "cover_image": "data:image/jpeg;base64,SECOND",
        },
    )

    res_u1 = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    res_u2 = client.get("/songs/disliked", params={"listener_id": "u2"}).json()
    assert res_u1["items"][0]["cover_image"] == "data:image/jpeg;base64,FIRST"
    assert res_u2["items"][0]["cover_image"] == "data:image/jpeg;base64,FIRST"


def _dislike(client, listener_id, artist, title):
    return client.post(
        "/songs/rating",
        json={"artist": artist, "title": title, "listener_id": listener_id, "rating": "down"},
    )


def test_disliked_songs_uses_configured_default_page_size(client, monkeypatch):
    import app.main

    monkeypatch.setattr(app.main.settings, "disliked_songs_page_size", 2)

    for i in range(5):
        _dislike(client, "u1", f"Artist {i}", f"Song {i}")

    res = client.get("/songs/disliked", params={"listener_id": "u1"}).json()
    assert res["page_size"] == 2
    assert len(res["items"]) == 2
    assert res["total"] == 5


def test_disliked_songs_explicit_page_size_overrides_default(client, monkeypatch):
    import app.main

    monkeypatch.setattr(app.main.settings, "disliked_songs_page_size", 5)

    for i in range(5):
        _dislike(client, "u1", f"Artist {i}", f"Song {i}")

    res = client.get(
        "/songs/disliked", params={"listener_id": "u1", "page_size": 3}
    ).json()
    assert res["page_size"] == 3
    assert len(res["items"]) == 3
    assert res["total"] == 5


def test_disliked_songs_second_page_returns_remaining_items(client):
    for i in range(5):
        _dislike(client, "u1", f"Artist {i}", f"Song {i}")

    page1 = client.get(
        "/songs/disliked", params={"listener_id": "u1", "page_size": 2, "page": 1}
    ).json()
    page2 = client.get(
        "/songs/disliked", params={"listener_id": "u1", "page_size": 2, "page": 2}
    ).json()
    page3 = client.get(
        "/songs/disliked", params={"listener_id": "u1", "page_size": 2, "page": 3}
    ).json()

    all_titles = [s["title"] for s in page1["items"] + page2["items"] + page3["items"]]
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) == 1
    assert len(set(all_titles)) == 5  # no duplicates, no gaps
    assert page1["total"] == page2["total"] == page3["total"] == 5


def test_disliked_songs_page_beyond_range_returns_empty(client):
    _dislike(client, "u1", "Artist A", "Song A")

    res = client.get(
        "/songs/disliked", params={"listener_id": "u1", "page": 5, "page_size": 5}
    ).json()
    assert res["items"] == []
    assert res["total"] == 1


def test_disliked_songs_invalid_page_rejected(client):
    res = client.get("/songs/disliked", params={"listener_id": "u1", "page": 0})
    assert res.status_code == 422


def test_disliked_songs_invalid_page_size_rejected(client):
    res = client.get("/songs/disliked", params={"listener_id": "u1", "page_size": 0})
    assert res.status_code == 422

    res = client.get("/songs/disliked", params={"listener_id": "u1", "page_size": 101})
    assert res.status_code == 422
