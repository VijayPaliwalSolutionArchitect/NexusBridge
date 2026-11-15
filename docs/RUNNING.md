# NexusBridge — Running Locally

## Start the server

```bash
cd backend
source .venv/Scripts/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration (environment variables / `.env`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSBRIDGE_DB_PATH` | `<root>/data/nexusbridge.db` | SQLite database file |
| `NEXUSBRIDGE_DATA_DIR` | `<root>/data` | Data directory |
| `NEXUSBRIDGE_FRONTEND_DIR` | `<root>/frontend` | Static web workspace |
| `NEXUSBRIDGE_HOST` | `0.0.0.0` | Bind host |
| `NEXUSBRIDGE_PORT` | `8000` | Bind port |

Copy `.env.example` to `.env` and adjust. `pydantic-settings` loads `.env`
automatically from the backend directory.

## Smoke-test the API

```bash
# List seeded connectors
curl http://127.0.0.1:8000/api/connectors

# Dry-run a mapping (no persistence)
curl -X POST http://127.0.0.1:8000/api/preview/1 -H 'Content-Type: application/json' \
  -d '{"payload":[{"Name":"Eve","Email":"EVE@EXAMPLE.COM","Type":"lead","Region_Code":"EU"}]}'

# Fire the seeded write-back webhook
curl -X POST http://127.0.0.1:8000/api/webhooks/hooks/customer-sync

# Run a sync job → persisted run log
curl -X POST http://127.0.0.1:8000/api/jobs/1/run

# Dashboard aggregates
curl http://127.0.0.1:8000/api/dashboard
```

## Tests

```bash
python -m pytest            # 22 passed
python -m pytest -q         # quiet
```

## Troubleshooting

- **Port already in use** → change `NEXUSBRIDGE_PORT` or kill the process on 8000.
- **DB locked** → stop all uvicorn workers; SQLite handles one writer at a time.
- **Frontend not found** → the API still works; the workspace 404s. Check
  `NEXUSBRIDGE_FRONTEND_DIR`.
