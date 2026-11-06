# URL Shortener

This is a URL shortener app built using Flask and Python.

## Features

- Shorten any http(s) URL with a random 6-character code (cryptographically random) or your own alias.
- **Input validation:** only http/https URLs are accepted, so `javascript:` and `data:` links can't be turned into redirects. Aliases are restricted to `[A-Za-z0-9_-]{3,32}` and reserved words are blocked.
- **Click analytics:** every redirect is counted with an atomic SQL increment; view them at `/stats/<code>` or the JSON API.
- **JSON API** alongside the web form.
- **Persistent storage** with SQLAlchemy: SQLite locally, Postgres in production via `DATABASE_URL`.
- **Rate limiting** on link creation (default 10/min per IP).
- Health check at `/healthz`, automated tests and CI.

## Live Demo

Check out the live demo of the URL shortener app [here](https://url-shortener-n6zk.onrender.com/). (The free Render instance sleeps when idle, so the first request can take ~30s.)

## API

```bash
# create
curl -X POST https://url-shortener-n6zk.onrender.com/api/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/some/long/path", "alias": "my-link"}'
# -> 201 {"code":"my-link","short_url":".../my-link","url":"https://example.com/some/long/path"}

# stats
curl https://url-shortener-n6zk.onrender.com/api/stats/my-link
# -> {"clicks": 3, "code": "my-link", "created_at": "...", "url": "..."}
```

Errors return `400` with `{"error": "..."}`; exceeding the rate limit returns `429`.

## Screenshots

![Homepage](https://github.com/eshanpandey/Url-Shortener/assets/56771531/196e34bc-2a41-4a90-9675-284956995bf7)
![Shortened URL](https://github.com/eshanpandey/Url-Shortener/assets/56771531/bc6f3a95-e679-4a6a-b146-c828d27df6c2)

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///shortener.db` | Database. Use a Postgres URL in production (e.g. Neon) so links survive redeploys. |
| `CREATE_LIMIT` | `10 per minute` | Rate limit on creating links, per IP |
| `RATELIMIT_STORAGE_URI` | `memory://` | Use `redis://...` to share limits across workers |

On Render the start command is `gunicorn app:app`. Note that Render's free disk is ephemeral, so set `DATABASE_URL` to a hosted Postgres to keep links.

## How to Run Locally

```bash
pip install -r requirements.txt -r requirements-dev.txt
python app.py        # http://localhost:5000
pytest               # run the tests
```

## Next Steps

- User accounts so people can manage their own links.
- Link expiry and QR codes.
- Redis cache for hot redirects.
