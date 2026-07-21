"""Regression test for a bug where ratings appeared to submit successfully in the
UI but never persisted (silently failing writes to a real, file-backed SQLite DB,
as opposed to the in-memory DB used by the other tests)."""

import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def file_backed_client(tmp_path, monkeypatch):
    db_path = tmp_path / "radiostation.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import app.Configuration.config
    import app.utilities.database
    import app.models
    import app.main

    importlib.reload(app.Configuration.config)
    importlib.reload(app.utilities.database)
    importlib.reload(app.models)
    importlib.reload(app.main)

    with TestClient(app.main.app) as test_client:
        yield test_client

    importlib.reload(app.Configuration.config)
    importlib.reload(app.utilities.database)
    importlib.reload(app.models)
    importlib.reload(app.main)


def test_rating_persists_to_disk_and_survives_reread(file_backed_client):
    client = file_backed_client

    post_res = client.post(
        "/songs/rating",
        json={"artist": "SOS Band", "title": "Take Your Time", "listener_id": "u1", "rating": "up"},
    )
    assert post_res.status_code == 201
    assert post_res.json()["thumbs_up"] == 1

    get_res = client.get(
        "/songs/rating",
        params={"artist": "SOS Band", "title": "Take Your Time", "listener_id": "u1"},
    )
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["thumbs_up"] == 1
    assert body["user_rating"] == "up"
