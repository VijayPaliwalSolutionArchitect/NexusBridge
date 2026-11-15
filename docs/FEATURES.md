# NexusBridge — Features

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

Feature list mapped to the actual implementation. ✅ = implemented and tested;
◻ = planned (playbook scope, not yet in code).

## Connector registry — ✅
- Full CRUD for connectors (`routers/connectors.py`): name, `type`
  (`rest | db | queue`), `base_url`, `auth_type` label, notes.
- Stores **no secrets** — `auth_type` is only a label (`none|bearer|basic`).
- Seeded with demo connectors on first boot.

## Field-mapping studio — ✅
- Mappings bind `source_connector_id` → `target_connector_id`
  (`routers/mappings.py`) with ordered **field rules** (`routers/mappings.py`
  + `models.py`): `source_field`, `target_field`, `transform`, optional
  `transform_param`, `sort_order`.
- Transforms implemented in `engine.py`: `direct`, `upper`, `lower`, `concat`,
  `const`. Missing source fields are reported per-row as errors, not crashes.

## Preview / dry-run — ✅
- `POST /api/preview/{mapping_id}` runs a mapping against an arbitrary payload
  **without persisting anything** (`routers/preview.py` + `engine.run_preview`).
- Returns `{mapping_id, input_rows, output_rows, errors}` — the guardrail for
  testing a mapping before activation.

## Job orchestration (simulated) — ✅
- Jobs CRUD (`routers/jobs.py`) with `status` (`active|paused`) and
  human-readable `schedule_note` (no real scheduler — execution is on-demand).
- `POST /api/jobs/{id}/run` executes the pipeline: fetch source rows
  (simulated from the mapping's demo payload) → transform → persist a run log.
- Every run is written to `run_logs` (audit trail): status, rows in/out,
  error, output snapshot, timestamps.

## Webhook triggers — ✅
- Register a `path` + `method` bound to a job (`routers/webhooks.py`).
- `POST /api/webhooks/hooks/{path}` fires the bound job and returns the
  `RunResult` — the simulated "write-back into M365/D365 orchestrated by
  n8n / Power Automate" path.

## Governance dashboard — ✅
- `GET /api/dashboard` aggregates: totals (jobs, runs, rows), active vs paused,
  per-job success/failure counts and error rate, recent runs.
- Backed by SQL in `database.py` over `jobs` + `run_logs`.

## Web workspace UI — ✅
- Single-page vanilla JS SPA at `frontend/` served at `/`: tabs for Dashboard,
  Connectors, Mappings, Jobs, Webhooks; calls the `/api/*` routes.
- Zero build step (no node_modules).

## Observability & health — ✅
- `GET /api/health` liveness probe; automatic `/docs`, `/redoc`,
  `/api/openapi.json` from FastAPI.
- Structured run logs in SQLite (queryable audit trail).

## Security / auth — ◻ (out of scope for the reference build)
- No authentication on the API and no stored credentials by design. A
  production derivative would add Entra ID OAuth (delegated Graph
  permissions) — planned, not implemented.

## Real schedulers & real network I/O — ◻
- `schedule_note` is informational only; no cron/APScheduler yet.
- Connector "fetch" is simulated from demo payloads; no live HTTP calls yet.

## Multi-tenant / RBAC — ◻
- Single-tenant reference implementation.
