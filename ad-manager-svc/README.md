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
| `API_KEY` | no | One key, or several separated by commas. When set, every route except `/health` needs it. See below |
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

## API key

With `API_KEY` set, a request must send it in the `X-API-Key` header, or it gets `401 {"error": "missing or invalid API key"}`. `/health` is always open so the Kubernetes probes work, and so are browser preflight (`OPTIONS`) requests, which cannot carry a header. With `API_KEY` unset the API is open, as it was before this check existed, and a warning is logged at startup.

To rotate a key, put the new one next to the old (`API_KEY=new,old`), update the callers (the ad server and the refresh service send `AD_MANAGER_API_KEY`, the dashboard asks for it), then remove the old one. Keys are compared as SHA-256 digests with `hmac.compare_digest`.

This is one shared key. It says the caller is trusted, not who they are.

## Migrations

The schema is also defined by Alembic migrations in `migrations/`. The service itself still only creates missing tables on startup.

```
export DATABASE_URL=postgresql://user:pass@localhost:5432/adpulse
alembic upgrade head      # a new, empty database
alembic stamp head        # a database the service already created, so it is not migrated again
alembic check             # fails if the models and the database differ
alembic revision --autogenerate -m "what changed"   # after you change a model, then read the file it writes
```

Do not run `alembic upgrade head` on a database the service has already created. The baseline would try to create tables that exist. Use `stamp` there. CI checks both paths: a migrated database and a service-created one come out with the same schema.

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
  empty (the response then has a `field` when Postgres says which one), an id
  points at a row that does not exist, or a value is in the wrong format for its
  column, such as a date Postgres cannot read. Postgres decides what is readable,
  so the API accepts what the database accepts (the dashboard sends some numbers
  as strings, and Postgres reads them)
- 401: `API_KEY` is set and the key is missing or wrong
- 404: the id was not found
- 502: creative storage (Supabase) could not be reached
- 500: anything unexpected. The details go to the log, not to the client.

## Testing

```
python -m unittest discover -s app/test -p "*_test.py"
```

With a coverage table (`pip install coverage`):

```
python -m coverage run --source=. --omit="*/test/*,migrations/*" -m unittest discover -s app/test -p "*_test.py"
python -m coverage report
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
