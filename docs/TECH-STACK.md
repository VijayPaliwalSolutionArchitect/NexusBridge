# NexusBridge — Tech Stack

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

Everything below is pinned/derived from the actual project files:
`backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pyproject.toml`.

## Runtime

| Technology | Version constraint | Source | Why chosen |
|---|---|---|---|
| Python | ≥ 3.11 (developed on 3.14) | `pyproject.toml` `requires-python` | Modern stdlib (`sqlite3`, `datetime.UTC`), type hints |
| FastAPI | ≥ 0.110 | `requirements.txt` | Async-capable API framework with automatic OpenAPI/Swagger docs and Pydantic validation |
| Uvicorn `[standard]` | ≥ 0.29 | `requirements.txt` | Fast ASGI server; `[standard]` adds `uvloop` + `httptools` |
| Pydantic | ≥ 2.6 | `requirements.txt` | v2 request/response models (`models.py`) — validation + OpenAPI schema for free |
| SQLite (stdlib `sqlite3`) | built into Python | `database.py` | Zero-ops persistence; one file = trivial backups (see DEPLOYMENT.md) |

## Dev / test

| Technology | Version constraint | Source | Why chosen |
|---|---|---|---|
| pytest | ≥ 8.0 | `requirements-dev.txt` | Test runner (`pyproject.toml` sets `testpaths = ["tests"]`) |
| httpx | ≥ 0.27 | `requirements-dev.txt` | Powers FastAPI's `TestClient` for API tests without a live server |

## Frontend

| Technology | Version | Source | Why chosen |
|---|---|---|---|
| Vanilla HTML/CSS/JS (ES6) | — | `frontend/index.html`, `app.js`, `styles.css` | Zero build step, zero `node_modules`, served as static files by FastAPI's `StaticFiles` |

## Data model (SQLite schema in `database.py`)

```
connectors(id, name, type, base_url, auth_type, notes, created_at)
mappings(id, name, source_connector_id, target_connector_id, created_at)
mapping_fields(id, mapping_id, source_field, target_field, transform, transform_param, sort_order)
jobs(id, name, source_connector_id, target_connector_id, mapping_id, schedule_note, status, created_at)
run_logs(id, job_id, started_at, finished_at, status, rows_in, rows_out, error, output_json)
webhooks(id, job_id, path, method, active, created_at)
```

## Architecture-relevant choices

| Decision | Rationale |
|---|---|
| SQLite over Postgres | Reference implementation is single-node; swapping the `database.py` layer is the only change needed to go multi-node |
| Stdlib `.env` parser in `config.py` | Avoids a `python-dotenv` dependency; `.env` stays optional |
| Deterministic engine (`engine.py`) | Fully offline — reproducible tests, no network flakiness, no secrets |
| No auth in reference build | Nothing to protect (no credentials stored); production notes in DEPLOYMENT.md §7 |

## Not used (deliberately)

- No `python-dotenv`, no ORM (raw `sqlite3` with row factory), no Celery/APScheduler,
  no Docker requirement for local dev, no npm/build tooling for the frontend.
