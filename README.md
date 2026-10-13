---
title: AI
emoji: 🚀
colorFrom: red
colorTo: purple
sdk: docker
pinned: false
---

# AI Photo Sharing

A host uploads the photos of an event. Each guest opens a link, takes a selfie, and gets
every photo they appear in. Built for weddings, family functions, poojas and garba nights.

## How it works

```
Host page  ──upload──▶  Flask API  ──▶  face model (InsightFace, CPU)
                           │                 │ one embedding per face
                           ├──▶  PostgreSQL (Supabase): events, photos, embeddings, sessions
                           └──▶  photo storage (private Hugging Face dataset)

Guest page ──selfie──▶  Flask API  ──▶  compare with the event's embeddings
                           └──▶  signed, expiring links to the matching photos
```

| Folder | What is in it |
|---|---|
| `backend/api/` | HTTP routes: `photographer.py` (host), `user.py` (guest), `media.py` (photo links), `admin.py` |
| `backend/services/` | storage, matching, upload jobs, retention |
| `backend/database/` | connection pool, SQL (`repo.py`), `migrations/` |
| `backend/models/` | the face engine |
| `backend/security.py` | codes, keys, signed links |
| `static/` | the three pages and their scripts |
| `tests/` | unit tests, and `integration/` tests that need PostgreSQL |
| `benchmarks/` | accuracy measurement on your own labelled photos |
| `scripts/` | local dev server and diagnostics |

## Who can do what

Every event has three separate secrets:

| Secret | Who has it | What it allows |
|---|---|---|
| Guest code (`EVT-…`) | every guest, via link or QR code | search for their own photos |
| Contributor key (`ck_…`) | helpers the host chooses | upload photos, nothing else |
| Host key (`hk_…`) | the host only | upload, statistics, delete the event |

The keys are shown once when the event is created. Only their hashes are stored, so they
cannot be shown again; an admin can issue new ones (see below).

A guest's session can open only the photos it matched, plus the event's photos that contain
no faces (decor, rituals, venue). Photos are served only through links signed by the server
that expire. Selfies are deleted right after the search and never stored.

## Configuration

Copy `.env.example` to `.env` for local work. In production set the same names as secrets
on the host.

| Variable | Needed | Purpose |
|---|---|---|
| `SUPABASE_DATABASE_URL` | yes | PostgreSQL connection string |
| `HF_TOKEN`, `HF_DATASET_ID` | yes | private dataset that stores the photos |
| `APP_SECRET` | yes | signs photo links; a long random string that stays the same across restarts |
| `ADMIN_SECRET` | recommended | enables `/api/admin/*`; without it those endpoints do not exist |
| `RETENTION_DAYS` | no (90) | age after which an event may be purged |
| `RETENTION_AUTO_PURGE` | no (false) | purge expired events automatically once a day |
| `TRUSTED_PROXY_HOPS` | no (1) | reverse proxies in front of the app, for per-client rate limits |
| `SIMILARITY_THRESHOLD` | no (0.4) | match cutoff; set it from the benchmark |
| `SENTRY_DSN` | no | error reporting |

## Running locally

The face model needs native libraries and a large download. For work on the pages and the
API there is a dev server with a toy engine that treats an image's colour as its "face":

```bash
pip install -r requirements-test.txt
SUPABASE_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/postgres?sslmode=disable" \
  python scripts/dev_server.py
```

It needs any local PostgreSQL and stores photos on disk under `storage/`.

With the real model, use Docker:

```bash
docker build -t ai-photo-sharing .
docker run --env-file .env -p 7860:7860 ai-photo-sharing
```

## Tests

```bash
pip install -r requirements-test.txt
pytest
```

The SQL and migrations are tested against a real database when `TEST_DATABASE_URL` points
at a local, throwaway PostgreSQL (the tests wipe it first, and refuse any non-local host):

```bash
TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/postgres?sslmode=disable" pytest
```

GitHub Actions runs both, and builds the Docker image, on every branch (`.github/workflows/ci.yml`).

## Database changes

Schema changes are numbered SQL files in `backend/database/migrations/`. The app applies any
it has not yet applied when it starts, inside one transaction. To change the schema, add the
next numbered file; never edit one that has already run in production.

## Admin tasks

All need the header `X-Admin-Secret: <ADMIN_SECRET>`.

```bash
# Issue new keys for an event (events created before keys existed have none,
# and stay locked for upload until this is done). Old keys stop working.
curl -X POST -H "X-Admin-Secret: $ADMIN_SECRET" https://<host>/api/admin/events/<CODE>/keys

# List events past their retention period. Add ?dry_run=0 to delete them.
curl -X POST -H "X-Admin-Secret: $ADMIN_SECRET" https://<host>/api/admin/purge-expired

# Count selfies stored by older versions of the app. Add ?dry_run=0 to delete them.
curl -X POST -H "X-Admin-Secret: $ADMIN_SECRET" https://<host>/api/admin/purge-selfies
```

Deleting with the Hugging Face backend also squashes the dataset's git history, because a
file removed from a git repository otherwise stays recoverable from its history.

## Deploying

1. CI is green on the commit.
2. `APP_SECRET` and `ADMIN_SECRET` are set on the host.
3. Deploy. On start the app applies pending migrations.
4. `GET /api/ready` returns 200 once the model is loaded and the database is reachable.
   `GET /api/health` only says the web server is up.
5. For events that existed before upload keys, issue keys with the admin endpoint.

The Azure workflow (`deploy-acr.yml`) is manual: start it from the Actions tab.

## Face model licence

The app uses InsightFace's `buffalo_l` model pack. InsightFace publishes its pretrained
models for non-commercial research use only, so charging for this service needs either a
commercial licence from InsightFace or a switch to models that allow commercial use.
`FACE_MODEL_PACK` selects the pack, and every stored embedding records which model made it.
See `ROADMAP.md` (step 0.1) and `benchmarks/` for comparing models before switching.
