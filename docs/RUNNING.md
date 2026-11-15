# NexusBridge — Running Locally

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

## 1. Start the server

From `backend/` with the venv active:

```bash
# Development (auto-reload on code changes)
uvicorn app.main:app --reload

# Production-style single process
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Host/port can also come from the environment (see §3)
NEXUSBRIDGE_HOST=127.0.0.1 NEXUSBRIDGE_PORT=8000 uvicorn app.main:app
```

On boot the app creates/seeds `data/nexusbridge.db` (see
[INSTALLATION.md](INSTALLATION.md)) and mounts the static workspace at `/`.

## 2. URLs

| URL | What |
|---|---|
| <http://127.0.0.1:8000/> | Web workspace SPA (dashboard, connectors, mappings, jobs, webhooks tabs) |
| <http://127.0.0.1:8000/docs> | Swagger UI (interactive API console) |
| <http://127.0.0.1:8000/redoc> | ReDoc |
| <http://127.0.0.1:8000/api/openapi.json> | Raw OpenAPI schema |
| <http://127.0.0.1:8000/api/health> | Liveness probe → `{"service":"nexusbridge","version":"1.0.0","status":"ok"}` |

## 3. Environment variables

Loaded from `.env` at the project root if present (copy `.env.example`).
Full reference with examples: [env-config.md](env-config.md).

| Variable | Default | Effect |
|---|---|---|
| `NEXUSBRIDGE_DATA_DIR` | `<project root>/data` | Where runtime data lives |
| `NEXUSBRIDGE_DB_PATH` | `<NEXUSBRIDGE_DATA_DIR>/nexusbridge.db` | SQLite file (`:memory:` also works) |
| `NEXUSBRIDGE_FRONTEND_DIR` | `<project root>/frontend` | Static SPA directory mounted at `/` |
| `NEXUSBRIDGE_HOST` | `0.0.0.0` | Bind host for uvicorn |
| `NEXUSBRIDGE_PORT` | `8000` | Bind port for uvicorn |

## 4. Endpoint walkthrough (curl)

Base URL: `http://127.0.0.1:8000`

```bash
# Health
curl http://127.0.0.1:8000/api/health

# ---- Connectors: list / create / read / update / delete ----
curl http://127.0.0.1:8000/api/connectors
curl -X POST http://127.0.0.1:8000/api/connectors \
  -H 'Content-Type: application/json' \
  -d '{"name":"CRM export","type":"rest","base_url":"https://crm.example.com/api","auth_type":"bearer","notes":"demo"}'
curl http://127.0.0.1:8000/api/connectors/1
curl -X PUT http://127.0.0.1:8000/api/connectors/1 \
  -H 'Content-Type: application/json' -d '{"name":"CRM export v2"}'
curl -X DELETE http://127.0.0.1:8000/api/connectors/3        # -> 204 No Content

# ---- Mappings: CRUD with nested field rules ----
curl http://127.0.0.1:8000/api/mappings
curl -X POST http://127.0.0.1:8000/api/mappings \
  -H 'Content-Type: application/json' \
  -d '{"name":"Leads to CRM","source_connector_id":1,"target_connector_id":2,
       "field_rules":[
         {"source_field":"Name","target_field":"full_name","transform":"direct","sort_order":1},
         {"source_field":"Email","target_field":"email","transform":"lower","sort_order":2}]}'

# ---- Preview: dry-run a mapping against an arbitrary payload (NOT persisted) ----
curl -X POST http://127.0.0.1:8000/api/preview/1 \
  -H 'Content-Type: application/json' \
  -d '{"payload":[{"Name":"Eve","Email":"EVE@EXAMPLE.COM","Type":"lead","Region_Code":"EU"}]}'
# -> {"mapping_id":1,"input_rows":1,"output_rows":[...],"errors":[...]}

# ---- Jobs: CRUD + run ----
curl http://127.0.0.1:8000/api/jobs
curl -X POST http://127.0.0.1:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"name":"Nightly lead sync","source_connector_id":1,"target_connector_id":2,
       "mapping_id":1,"schedule_note":"daily 02:00","status":"active"}'
curl -X POST http://127.0.0.1:8000/api/jobs/1/run
# -> RunResult {job_id, status, rows_in, rows_out, error, output, started_at, finished_at}

# ---- Webhooks: register a write-back trigger, then fire it ----
curl -X POST http://127.0.0.1:8000/api/webhooks \
  -H 'Content-Type: application/json' \
  -d '{"job_id":1,"path":"/hooks/customer-sync","method":"POST","active":1}'
curl -X POST http://127.0.0.1:8000/api/webhooks/hooks/customer-sync
# -> RunResult of the bound job (404 if no webhook matches the path)

# ---- Dashboard: aggregate governance stats ----
curl http://127.0.0.1:8000/api/dashboard
```

Full request/response schemas: [API.md](API.md).

## 5. Run the tests

```bash
cd backend
python -m pytest                          # 22 passed
python -m pytest tests/test_engine.py -v  # engine unit tests only
python -m pytest tests/test_api.py -v     # HTTP API tests only
```

Tests use `httpx.TestClient` against an isolated throwaway SQLite database, so
they never touch your `data/nexusbridge.db`.

## 6. Stopping

`Ctrl+C` in the uvicorn terminal. SQLite commits on every write, so no
shutdown hook is needed.
