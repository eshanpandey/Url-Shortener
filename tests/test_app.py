import pytest

from app import create_app, db


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/t.db",
        "CREATE_LIMIT": "1000 per minute",
    })
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.session.remove()
        db.drop_all()


def shorten(client, url, alias=None):
    return client.post("/api/shorten", json={"url": url, "alias": alias})


def test_shorten_and_redirect(client):
    r = shorten(client, "https://example.com/page")
    assert r.status_code == 201
    code = r.get_json()["code"]
    assert len(code) == 6
    r = client.get(f"/{code}")
    assert r.status_code == 302
    assert r.headers["Location"] == "https://example.com/page"


def test_scheme_is_added_when_missing(client):
    assert shorten(client, "example.com").get_json()["url"] == "https://example.com"


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://x.com/f", "data:text/html,hi", "", "http://", "https:///x"])
def test_rejects_unsafe_or_invalid_urls(client, bad):
    assert shorten(client, bad).status_code == 400


def test_custom_alias_and_conflict(client):
    assert shorten(client, "https://a.com", "my-link").status_code == 201
    assert shorten(client, "https://b.com", "my-link").status_code == 400
    assert client.get("/my-link").headers["Location"] == "https://a.com"


@pytest.mark.parametrize("alias", ["ab", "has space", "x" * 33, "api", "stats", "bad!"])
def test_rejects_bad_aliases(client, alias):
    assert shorten(client, "https://a.com", alias).status_code == 400


def test_click_counting(client):
    code = shorten(client, "https://a.com").get_json()["code"]
    for _ in range(3):
        client.get(f"/{code}")
    assert client.get(f"/api/stats/{code}").get_json()["clicks"] == 3


def test_unknown_code_404(client):
    assert client.get("/nope123").status_code == 404
    assert client.get("/api/stats/nope123").status_code == 404


def test_html_form_flow_and_error_display(client):
    ok = client.post("/", data={"long_url": "https://a.com", "custom_short_url": "form-link"})
    assert ok.status_code == 200 and b"/form-link" in ok.data
    dup = client.post("/", data={"long_url": "https://b.com", "custom_short_url": "form-link"})
    assert dup.status_code == 400 and b"already taken" in dup.data


def test_rate_limit(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/r.db", "CREATE_LIMIT": "2 per minute"})
    c = app.test_client()
    codes = [shorten(c, "https://a.com").status_code for _ in range(3)]
    assert codes == [201, 201, 429]


def test_health(client):
    assert client.get("/healthz").data == b"ok"


def test_host_with_port_is_accepted(client):
    assert shorten(client, "localhost:8080/path").get_json()["url"] == "https://localhost:8080/path"
