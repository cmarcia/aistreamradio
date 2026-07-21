def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_and_list_genres(client):
    payload = {"name": "Synthwave", "description": "80s Retro Electronic"}
    res = client.post("/genres", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "Synthwave"
    assert "id" in created

    res = client.get("/genres")
    assert res.status_code == 200
    genres = res.json()
    assert any(g["name"] == "Synthwave" for g in genres)

    res = client.get(f"/genres/{created['id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "Synthwave"


def test_stations_auto_seeding_when_empty(client):
    res = client.get("/stations")
    assert res.status_code == 200
    stations = res.json()
    assert len(stations) == 9
    station_names = [s["name"] for s in stations]
    assert "Galglatz (גלגלצ)" in station_names
    assert "Metal Detector" in station_names
    assert "Classic Rock Vault" in station_names
    assert "WQXR 105.9 FM Classical" in station_names
    assert "Klassik Radio Symphony" in station_names
    for s in stations:
        assert s["stream_url"].startswith("http") or s["stream_url"].startswith("/")
        assert s["metadata_url"].startswith("http") or s["metadata_url"].startswith("/")
        assert s["genre"] is not None
        assert "name" in s["genre"]


def test_create_and_list_stations(client):
    genre_res = client.post("/genres", json={"name": "Indie Alternative"})
    genre_id = genre_res.json()["id"]

    payload = {
        "name": "KEXP",
        "frequency": "90.3 FM",
        "genre_id": genre_id,
        "stream_url": "https://example.com/stream.m3u8",
        "metadata_url": "https://example.com/meta.json",
    }
    res = client.post("/stations", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "KEXP"
    assert created["stream_url"] == "https://example.com/stream.m3u8"
    assert "id" in created

    res = client.get("/stations")
    assert res.status_code == 200
    stations = res.json()
    assert len(stations) == 1
    assert stations[0]["name"] == "KEXP"
    assert stations[0]["genre"]["name"] == "Indie Alternative"


def test_create_station_default_fallback_urls(client):
    payload = {"name": "SomaFM Groove Salad", "frequency": "Online"}
    res = client.post("/stations", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "SomaFM Groove Salad"
    assert created["stream_url"] == "https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8"
    assert created["metadata_url"] == "https://d3d4yli4hf5bmh.cloudfront.net/metadata.json"


def test_get_station_by_id(client):
    created = client.post(
        "/stations", json={"name": "WNYC", "frequency": "93.9 FM"}
    ).json()

    res = client.get(f"/stations/{created['id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "WNYC"
    assert "stream_url" in res.json()
    assert "metadata_url" in res.json()


def test_get_station_not_found(client):
    res = client.get("/stations/999")
    assert res.status_code == 404
