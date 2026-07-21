def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_index_page_links_external_stylesheet(client):
    res = client.get("/")
    assert '<link rel="stylesheet" href="/static/CSS/style.css">' in res.text
    assert "<style>" not in res.text


def test_stylesheet_served_at_static_path(client):
    res = client.get("/static/CSS/style.css")
    assert res.status_code == 200
    assert "text/css" in res.headers["content-type"]
    assert ".rate button" in res.text


def test_index_page_links_external_scripts_in_dependency_order(client):
    res = client.get("/")
    expected_order = [
        '<script src="/static/Script/formatters.js"></script>',
        '<script src="/static/Script/util.js"></script>',
        '<script src="/static/Script/player.js"></script>',
        '<script src="/static/Script/rating.js"></script>',
        '<script src="/static/Script/disliked.js"></script>',
        '<script src="/static/Script/main.js"></script>',
    ]
    positions = [res.text.index(tag) for tag in expected_order]
    assert positions == sorted(positions)
    # no application logic should be embedded directly in the page
    assert "function pollMetadata" not in res.text


def test_app_scripts_served_at_static_path(client):
    for filename, expected_content in [
        ("formatters.js", "function formatTime"),
        ("util.js", "function apiFetch"),
        ("player.js", "function initHls"),
        ("rating.js", "function setRating"),
        ("disliked.js", "function fetchDislikedSongs"),
        ("main.js", "function pollMetadata"),
    ]:
        res = client.get(f"/static/Script/{filename}")
        assert res.status_code == 200
        assert "javascript" in res.headers["content-type"]
        assert expected_content in res.text
