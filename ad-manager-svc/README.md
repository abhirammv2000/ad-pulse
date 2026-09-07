# ad-manager-svc

Flask API for the ad inventory/demand data model — publishers, ad units,
advertisers, campaigns, ads and creatives — plus the endpoints that refresh
the Redis cache ad-server-svc reads from, and the `/reports` endpoints backed
by MongoDB.

## Configuration

All via environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string |
| `MONGODB_URI` | yes | MongoDB connection string, for `/reports` |
| `MONGODB_DATABASE` | no (default `ad_pulse`) | Mongo database name |
| `REDIS_HOST` | no (default `localhost`) | Redis host for the serving cache |
| `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD` | no | Redis auth |
| `SUPABASE_URL`, `SUPABASE_KEY` | only for `/creative/upload` | Object storage for creative assets |
| `SUPABASE_BUCKET` | no (default `Creatives`) | Storage bucket/folder name |
| `CORS_ALLOWED_ORIGINS` | no (default `*`) | Comma-separated allowed origins |
| `FLASK_DEBUG` | no | Set to `1`/`true` to enable the Werkzeug debugger locally — never in production |

## Running

```
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/adpulse
export MONGODB_URI=mongodb://localhost:27017
python run.py
```

The container image runs `gunicorn` against `run:app` instead.

## Testing

```
python -m unittest discover -s app/test -p "*_test.py"
```

## Layout

- `app/models/` — one SQLAlchemy model per table, all sharing one declarative
  base (`app/models/base.py`) so the cross-table `ForeignKey`s resolve, plus a
  `to_dict()` used to serialize rows without repeating every column name.
- `app/services/` — one module per entity; the shared read/update helpers live
  in `app/services/crud.py`.
- `app/routes/` — Flask blueprints; thin, no business logic.
- `app/cache/` — rebuilds the Redis projection of active campaigns/ads/creatives
  that ad-server-svc serves from.
