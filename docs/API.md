# NexusBridge — API Reference

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

- **Base URL:** `http://127.0.0.1:8000`
- **Interactive docs:** `/docs` (Swagger UI), `/redoc`, raw schema at `/api/openapi.json`
- **Auth:** none — local reference implementation; no credentials are read or stored
- **Errors:** FastAPI standard shape — `{"detail": "..."}` for 404/400, `422` with
  `{"detail": [{loc, msg, type}, ...]}` for validation failures; `DELETE` endpoints return `204 No Content`.

All routes below are derived from the actual routers in `backend/app/routers/`.

---

## System

### `GET /api/health`
Liveness probe.

```bash
curl http://127.0.0.1:8000/api/health
```
```json
{"service": "nexusbridge", "version": "1.0.0", "status": "ok"}
```

---

## Connectors — `/api/connectors` (`routers/connectors.py`)

A connector describes a source/target system. Only **non-secret** metadata is
stored (`auth_type` is a label like `bearer|basic|none`; no tokens).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/connectors` | List all connectors |
| `POST` | `/api/connectors` | Create a connector → `201` |
| `GET` | `/api/connectors/{connector_id}` | Read one (404 if missing) |
| `PUT` | `/api/connectors/{connector_id}` | Partial update |
| `DELETE` | `/api/connectors/{connector_id}` | Delete → `204` |

**Create body (`ConnectorCreate`):**

```bash
curl -X POST http://127.0.0.1:8000/api/connectors \
  -H 'Content-Type: application/json' \
  -d '{"name":"CRM export","type":"rest","base_url":"https://crm.example.com/api","auth_type":"bearer","notes":"demo"}'
```
```json
{"name": "CRM export", "type": "rest", "base_url": "https://crm.example.com/api",
 "auth_type": "bearer", "notes": "demo"}
```

**Response (`ConnectorOut`):** `{id, name, type, base_url, auth_type, notes, created_at}`

---

## Mappings — `/api/mappings` (`routers/mappings.py`)

A mapping binds a source connector to a target connector and carries ordered
**field rules** (transforms).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/mappings` | List mappings (with their field rules) |
| `POST` | `/api/mappings` | Create a mapping → `201` |
| `GET` | `/api/mappings/{mapping_id}` | Read one (404 if missing) |
| `PUT` | `/api/mappings/{mapping_id}` | Replace/update a mapping |
| `DELETE` | `/api/mappings/{mapping_id}` | Delete → `204` |

**Create body (`MappingCreate`)** — note `field_rules`:

```bash
curl -X POST http://127.0.0.1:8000/api/mappings \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Leads to CRM",
    "source_connector_id": 1,
    "target_connector_id": 2,
    "field_rules": [
      {"source_field":"Name","target_field":"full_name","transform":"direct","sort_order":1},
      {"source_field":"Email","target_field":"email","transform":"lower","sort_order":2},
      {"source_field":"Region_Code","target_field":"region","transform":"const","transform_param":"EU","sort_order":3}
    ]
  }'
```

**Transforms** (`engine._transform_value`):

| Transform | Effect |
|---|---|
| `direct` | Copy the value as-is |
| `upper` | Uppercase (strings only) |
| `lower` | Lowercase (strings only) |
| `concat` | Join `transform_param` + value |
| `const` | Emit `transform_param` regardless of input |

A missing source field produces a per-field error string
(`"Missing field: <Name>"`) instead of a crash.

---

## Preview (dry-run) — `/api/preview` (`routers/preview.py`)

### `POST /api/preview/{mapping_id}`

Dry-runs a mapping against an **arbitrary supplied payload** — nothing is
persisted. This is the guardrail for testing a mapping before activating it.

```bash
curl -X POST http://127.0.0.1:8000/api/preview/1 \
  -H 'Content-Type: application/json' \
  -d '{"payload":[{"Name":"Eve","Email":"EVE@EXAMPLE.COM","Type":"lead","Region_Code":"EU"}]}'
```
```json
{
  "mapping_id": 1,
  "input_rows": 1,
  "output_rows": [{"full_name": "Eve", "email": "eve@example.com", "region": "EU"}],
  "errors": []
}
```

---

## Jobs — `/api/jobs` (`routers/jobs.py`)

A job binds a mapping to a source→target connector pair and can be executed
(simulated) on demand.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/jobs` | List jobs |
| `POST` | `/api/jobs` | Create a job → `201` |
| `GET` | `/api/jobs/{job_id}` | Read one (404 if missing) |
| `PUT` | `/api/jobs/{job_id}` | Update (e.g. pause/resume via `status`) |
| `DELETE` | `/api/jobs/{job_id}` | Delete → `204` |
| `POST` | `/api/jobs/{job_id}/run` | Execute the simulation, persist a run log → `RunResult` |

**Create body (`JobCreate`):**

```bash
curl -X POST http://127.0.0.1:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"name":"Nightly lead sync","source_connector_id":1,"target_connector_id":2,
       "mapping_id":1,"schedule_note":"daily 02:00","status":"active"}'
```

`status` ∈ `active | paused`.

**Run:**

```bash
curl -X POST http://127.0.0.1:8000/api/jobs/1/run
```
```json
{
  "job_id": 1,
  "status": "success",
  "rows_in": 2,
  "rows_out": 2,
  "error": null,
  "output": [{"full_name": "..."}],
  "started_at": "2026-11-15T10:00:00",
  "finished_at": "2026-11-15T10:00:00"
}
```

The run is persisted to the `run_logs` table (audit trail). Per-row transform
errors are captured in `output`/`error` without failing the whole run.

---

## Webhooks — `/api/webhooks` (`routers/webhooks.py`)

Webhooks let an external system trigger a job — the simulated equivalent of a
write-back flow into M365/D365 orchestrated by n8n / Power Automate.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/webhooks` | List registered webhooks |
| `POST` | `/api/webhooks` | Register a webhook → `201` |
| `DELETE` | `/api/webhooks/{webhook_id}` | Remove → `204` |
| `POST` | `/api/webhooks/hooks/{path}` | Fire the webhook bound to `/hooks/{path}` → runs the bound job → `RunResult` (404 if none) |

```bash
curl -X POST http://127.0.0.1:8000/api/webhooks \
  -H 'Content-Type: application/json' \
  -d '{"job_id":1,"path":"/hooks/customer-sync","method":"POST","active":1}'

curl -X POST http://127.0.0.1:8000/api/webhooks/hooks/customer-sync
```

---

## Dashboard — `/api/dashboard` (`routers/dashboard.py`)

### `GET /api/dashboard`

Aggregate governance view: totals plus per-job stats and recent runs.

```bash
curl http://127.0.0.1:8000/api/dashboard
```
```json
{
  "total_jobs": 2, "active_jobs": 2, "paused_jobs": 0,
  "total_runs": 5, "total_rows_in": 10, "total_rows_out": 10,
  "overall_error_rate": 0.0,
  "jobs": [{"job_id": 1, "name": "Customer Sync", "status": "active",
            "total_runs": 3, "success_runs": 3, "failure_runs": 0,
            "error_rate": 0.0, "last_run_at": "2026-11-15T10:00:00"}],
  "recent_runs": [{"id": 5, "job_id": 1, "status": "success", "rows_in": 2, "rows_out": 2}]
}
```

---

## Static workspace

`GET /` serves `frontend/index.html` (the SPA calls the `/api/*` routes above).
The static mount is registered last so `/api/*`, `/docs`, `/redoc` keep precedence.
