# ad-manager-svc

Flask API for the ad inventory/demand data model: publishers, ad units,
advertisers, campaigns, ads and creatives, plus the endpoints that refresh
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
| `FLASK_DEBUG` | no | Set to `1`/`true` to enable the Werkzeug debugger locally; never in production |

## Running

```
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/adpulse
export MONGODB_URI=mongodb://localhost:27017
python run.py
```

The container image runs `gunicorn` against `run:app` instead.

## API behavior

Every entity has the same shape:

| Request | Result |
|---|---|
| `GET /<entity>` | all rows |
| `POST /<entity>` | create one (201) |
| `PUT /<entity>` | update the fields you send, keyed by the id in the body |
| `PATCH /<entity>?<entity>_id=...&state=ACTIVE` | change state. 400 for an unknown state, and nothing can go back to `CREATED` |
| `GET /<entity>/state/<state>` | rows in that state. 400 for an unknown state |

(The `<entity>` paths are `ad`, `adunit`, `advertiser`, `campaign`, `creative`
and `publisher`. Lookup-by-id paths differ a little, see `app/routes/`.)

Errors are always JSON, `{"error": "..."}`:

- 400: the body is not a JSON object, a state is invalid, a required column is
  empty, or an id points at a row that does not exist
- 404: the id was not found
- 502: creative storage (Supabase) could not be reached
- 500: anything unexpected. The details go to the log, not to the client.

## Testing

```
python -m unittest discover -s app/test -p "*_test.py"
```

## Layout

- `app/models/`: one SQLAlchemy model per table, all sharing one declarative
  base (`app/models/base.py`) so the cross-table `ForeignKey`s resolve, plus a
  `to_dict()` used to serialize rows without repeating every column name.
- `app/services/`: one module per entity; the shared read/update helpers live
  in `app/services/crud.py`.
- `app/routes/`: Flask blueprints; thin, no business logic. `helpers.py` holds
  what every entity shares: reading the JSON body and the `?state=` endpoints.
- `app/enums/states.py`: the five states an entity can be in.
- `app/cache/`: rebuilds the Redis projection of active campaigns/ads/creatives
  that ad-server-svc serves from.
