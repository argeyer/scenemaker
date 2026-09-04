# scenemaker backend

Backend for the scenemaker iPhone app. Users register, pick a movie scene
template, upload one or more selfies, and start a render job. A worker sends
the job to an external AI service and stores the finished video for the app to
download.

The iOS app lives in its own repository and talks to this service over the
REST API documented at `/docs` when the API is running.

## Features

- **Multitenant.** Every user, selfie, and job belongs to a tenant. Templates
  can be shared across tenants or private to one.
- **Two render modes.** `face_swap` replaces one or more actor faces with user
  selfies mapped to named slots. `avatar` builds an avatar from a selfie and
  inserts it with a predefined motion preset.
- **Credits.** Each render consumes one credit. Credits are granted by the
  billing integration (App Store purchases, not yet wired) and checked before
  a job is queued.
- **Pluggable backends.** Storage (local disk or S3-compatible), queue
  (in-memory or Redis), and AI service (fake or Hugging Face endpoint) are
  selected by environment variables.
- **Signed download links.** Template videos, selfies, and rendered outputs
  are served through time-limited URLs so the app never needs direct storage
  credentials.

## Architecture

```
iPhone app ──HTTPS──▶ API (FastAPI) ──▶ Postgres
                        │   ▲            ▲
                        │   │            │
                     push job id      job state
                        │                │
                        ▼                │
                     Redis queue ──▶ Worker ──▶ AI service (Hugging Face)
                                        │
                                        ▼
                                   Object storage (S3)
```

1. The app registers or logs in and receives a JWT scoped to the user's tenant.
2. The app lists templates and downloads the one the user picks.
3. The app uploads selfies. Each is stored and recorded in the database.
4. The app creates a job naming the template, the mode, and which selfie fills
   which slot. The API deducts a credit, saves the job as `queued`, and pushes
   its id onto the queue.
5. The worker pops the id, marks the job `running`, fetches the template video
   and selfies, calls the AI service, stores the returned video, and marks the
   job `done`. Failures are retried up to the configured attempt limit and then
   marked `failed` with the error.
6. The app polls the job until it is `done` and downloads the video from the
   signed `output_url`.

## Project layout

```
src/scenemaker/
  api/            FastAPI app, dependencies, and routers
  worker/         queue consumer and job processing
  db/             SQLAlchemy models and session setup
  schemas/        request and response models
  queue/          JobQueue protocol, memory and Redis implementations
  storage/        ObjectStorage protocol, local and S3 implementations
  ai/             VideoGenerator protocol, fake and Hugging Face implementations
  config.py       settings loaded from environment variables
  services.py     wires the chosen backends together
  seed.py         demo tenant and template for local development
  cli.py          `scenemaker api|worker|seed`
alembic/          database migrations
tests/            pytest suite (SQLite, in-memory queue, fake AI)
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a user in a tenant, returns a JWT |
| POST | `/auth/login` | Returns a JWT |
| GET | `/auth/me` | Current user and remaining credits |
| GET | `/templates` | Templates visible to the user's tenant |
| GET | `/templates/{id}` | Template detail with a signed video download URL |
| POST | `/selfies` | Upload a JPEG, PNG, or HEIC selfie (multipart) |
| GET | `/selfies` | The user's selfies |
| POST | `/jobs` | Queue a render job (consumes one credit) |
| GET | `/jobs` | The user's jobs |
| GET | `/jobs/{id}` | Job status and, when done, a signed `output_url` |
| GET | `/files/{key}` | Serves signed links when using local storage |

Example job request:

```json
{
  "template_id": "…",
  "kind": "face_swap",
  "selfies": [
    {"selfie_id": "…", "slot": "lead"},
    {"selfie_id": "…", "slot": "partner"}
  ]
}
```

For `avatar` jobs pass exactly one selfie in slot `avatar` and optionally a
`motion_preset` from the template's list.

## Local development

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

scenemaker seed          # creates the "demo" tenant and a sample template
scenemaker api --reload  # http://localhost:8000/docs
scenemaker worker        # in a second terminal
```

The defaults use SQLite, local disk storage under `./data`, an in-memory
queue, and the fake AI generator. Note that the in-memory queue is only
shared within one process, so with the defaults run the API and the worker
as one process during tests or switch to Redis to run them separately.

Grant yourself credits for testing by updating the `credits` column on your
user row.

### Docker Compose

Runs Postgres, Redis, the API, and the worker together:

```bash
cp .env.example .env
docker compose up --build
```

### Migrations

```bash
alembic upgrade head                          # apply
alembic revision --autogenerate -m "message"  # after changing models
alembic check                                 # verify models match migrations
```

### Tests and lint

```bash
pytest
ruff check .
ruff format .
```

## Configuration

All settings are environment variables prefixed with `SCENEMAKER_`. See
`.env.example` for the full list. The important ones:

| Variable | Values | Notes |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL | Use `postgresql+psycopg://…` in production |
| `JWT_SECRET` | string | At least 32 random bytes |
| `QUEUE_BACKEND` | `memory`, `redis` | Redis required when API and worker are separate processes |
| `STORAGE_BACKEND` | `local`, `s3` | S3 works with AWS, Cloudflare R2, and MinIO |
| `AI_BACKEND` | `fake`, `huggingface` | Hugging Face needs a token and two endpoint URLs |

## Hugging Face contract

The Hugging Face adapter posts a multipart request to the configured endpoint
with a `template` video file, one `selfie[<slot>]` file per slot, and a
`params` JSON field. It accepts a `video/*` response body, or JSON with either
`video_base64` or `video_url`. Adjust `ai/huggingface.py` to match the model
you deploy.

## Not yet implemented

- App Store purchase validation and server notifications to grant credits
- Admin endpoints for managing tenants and uploading templates
- Push notifications when a job finishes (the app polls for now)
- Face detection on upload to reject unusable selfies

## License

MIT
