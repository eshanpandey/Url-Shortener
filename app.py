"""URL shortener: Flask + SQLAlchemy (SQLite locally, Postgres via DATABASE_URL)."""
import os
import re
import secrets
import string
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Flask, jsonify, redirect, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

ALPHABET = string.ascii_letters + string.digits
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:(?!\d+(/|$))")
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED = {"api", "stats", "healthz", "static", "admin"}
MAX_URL_LEN = 2048

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


class Link(db.Model):
    code = db.Column(db.String(32), primary_key=True)
    long_url = db.Column(db.Text, nullable=False)
    clicks = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ValidationError(ValueError):
    pass


def normalize_url(raw):
    """Accept only http(s) URLs with a host; add https:// when the scheme is missing."""
    url = (raw or "").strip()
    if not url or len(url) > MAX_URL_LEN:
        raise ValidationError("Enter a URL up to %d characters." % MAX_URL_LEN)
    lower = url.lower()
    if not lower.startswith(("http://", "https://")):
        # "javascript:...", "data:...", "ftp://..." look like a scheme (a colon not
        # followed by a port number) and are rejected; bare hosts get https://.
        if SCHEME_RE.match(url):
            raise ValidationError("Only valid http(s) URLs can be shortened.")
        url = "https://" + url
    parts = urlsplit(url)
    try:
        parts.port  # raises ValueError on an invalid port
    except ValueError:
        raise ValidationError("Only valid http(s) URLs can be shortened.")
    if not parts.hostname:
        raise ValidationError("Only valid http(s) URLs can be shortened.")
    return url


def validate_alias(alias):
    alias = (alias or "").strip()
    if not alias:
        return None
    if not ALIAS_RE.match(alias):
        raise ValidationError("Alias must be 3-32 characters: letters, digits, - or _.")
    if alias.lower() in RESERVED:
        raise ValidationError("That alias is reserved.")
    return alias


def generate_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_link(long_url, alias=None):
    """Create a link; retry on the rare random-code collision. Returns the Link."""
    if alias:
        link = Link(code=alias, long_url=long_url)
        db.session.add(link)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValidationError("That alias is already taken.")
        return link
    for _ in range(5):
        link = Link(code=generate_code(), long_url=long_url)
        db.session.add(link)
        try:
            db.session.commit()
            return link
        except IntegrityError:
            db.session.rollback()
    raise RuntimeError("could not allocate a short code")


def create_app(config=None):
    app = Flask(__name__)
    uri = os.environ.get("DATABASE_URL", "sqlite:///shortener.db")
    if uri.startswith("postgres://"):  # Render/Heroku-style URLs
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=uri,
        RATELIMIT_STORAGE_URI=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        CREATE_LIMIT=os.environ.get("CREATE_LIMIT", "10 per minute"),
    )
    if config:
        app.config.update(config)
    db.init_app(app)
    limiter.init_app(app)
    with app.app_context():
        db.create_all()

    create_limit = lambda: app.config["CREATE_LIMIT"]  # noqa: E731

    @app.route("/", methods=["GET", "POST"])
    @limiter.limit(create_limit, methods=["POST"])
    def index():
        if request.method == "GET":
            return render_template("index.html")
        try:
            long_url = normalize_url(request.form.get("long_url"))
            alias = validate_alias(request.form.get("custom_short_url"))
            link = create_link(long_url, alias)
        except ValidationError as e:
            return render_template("index.html", error=str(e)), 400
        return render_template(
            "success.html",
            short_url=f"{request.host_url}{link.code}",
            stats_url=f"{request.host_url}stats/{link.code}",
        )

    @app.post("/api/shorten")
    @limiter.limit(create_limit)
    def api_shorten():
        data = request.get_json(silent=True) or {}
        try:
            long_url = normalize_url(data.get("url"))
            alias = validate_alias(data.get("alias"))
            link = create_link(long_url, alias)
        except ValidationError as e:
            return jsonify(error=str(e)), 400
        return jsonify(code=link.code, short_url=f"{request.host_url}{link.code}", url=link.long_url), 201

    @app.get("/api/stats/<code>")
    def api_stats(code):
        link = db.session.get(Link, code)
        if not link:
            return jsonify(error="not found"), 404
        return jsonify(code=link.code, url=link.long_url, clicks=link.clicks,
                       created_at=link.created_at.isoformat())

    @app.get("/stats/<code>")
    def stats(code):
        link = db.session.get(Link, code)
        if not link:
            return render_template("index.html", error="Short link not found."), 404
        return render_template("stats.html", link=link)

    @app.get("/healthz")
    def healthz():
        return "ok"

    @app.get("/<code>")
    def follow(code):
        link = db.session.get(Link, code)
        if not link:
            return render_template("index.html", error=f"No link found for '{code}'."), 404
        # Atomic increment in SQL: safe under concurrent requests.
        Link.query.filter_by(code=code).update({Link.clicks: Link.clicks + 1})
        db.session.commit()
        return redirect(link.long_url, code=302)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
