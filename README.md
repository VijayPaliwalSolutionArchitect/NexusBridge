# NexusBridge

**A connector-first data-integration and AI-copilot workspace** that unifies
Microsoft 365, Dynamics 365, SharePoint, and internal databases behind one
governed, permission-aware API. NexusBridge lets you register connectors,
describe field mappings, schedule/trigger sync jobs, preview the output of a
mapping *before* it runs, and trigger write-back flows via webhooks — all from
a single FastAPI process that also serves a small browser workspace.

> This is a **reference implementation**: every integration is simulated.
> The engine runs deterministic, canned sample payloads and never makes real
> network calls or stores credentials. It exists to demonstrate the data-flow
> and API surface (connectors → mappings → jobs → run logs → webhooks) that a
> production M365/D365 copilot workspace would expose.
>
> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

---

## What's inside

| Slice | Tech | Purpose |
|---|---|---|
| `backend/` | Python 3.14 · FastAPI · Pydantic v2 · stdlib `sqlite3` · Uvicorn | The entire REST API + transformation engine. |
| `frontend/` | Vanilla HTML/CSS/JS SPA | Browser workspace: dashboard, connectors, mappings, jobs, webhooks tabs. |
| `docs/` | GitHub-Flavored Markdown | Architecture, installation, running, API, features, tech stack, deployment, env config, playbook crosswalk. |
| `backend/tests/` | pytest · httpx TestClient | 22 passing tests covering engine + API + boot smoke. |

## Quick start

```bash
cd backend

# 1. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/Scripts/activate        # Windows (git-bash) — or .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt

# 2. Boot the API (it also serves the frontend workspace)
uvicorn app.main:app --reload
```

Open:

- Web workspace → <http://127.0.0.1:8000/>
- Interactive API docs → <http://127.0.0.1:8000/docs>
- Health check → <http://127.0.0.1:8000/api/health>

> The backend auto-creates `data/nexusbridge.db` (SQLite) on first boot and
> seeds it with sample connectors, mappings, jobs, a webhook, and run logs.
> `.gitignore` excludes the database and the virtualenv.

## Try it end to end

```bash
# List seeded connectors
curl http://127.0.0.1:8000/api/connectors

# Dry-run a mapping against an arbitrary payload (nothing is persisted)
curl -X POST http://127.0.0.1:8000/api/preview/1 -H 'Content-Type: application/json' \
  -d '{"payload":[{"Name":"Eve","Email":"EVE@EXAMPLE.COM","Type":"lead","Region_Code":"EU"}]}'

# Trigger the seeded write-back webhook (runs the Customer Sync simulation)
curl -X POST http://127.0.0.1:8000/api/webhooks/hooks/customer-sync

# Run a sync job and get a persisted run log with the transformed output
curl -X POST http://127.0.0.1:8000/api/jobs/1/run

# Aggregate governance stats
curl http://127.0.0.1:8000/api/dashboard
```

## Run the tests

```bash
cd backend
./.venv/Scripts/python.exe -m pytest          # Windows
# or:  python -m pytest                        # with active venv
```

Expect `22 passed`. Tests run against an isolated throwaway SQLite database
(never your `data/nexusbridge.db`).

## API surface

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/connectors` | List connectors |
| `POST` | `/api/connectors` | Create a connector |
| `GET/PUT/DELETE` | `/api/connectors/{id}` | Read / update / delete a connector |
| `GET`  | `/api/mappings` | List mappings (with field rules) |
| `POST` | `/api/mappings` | Create a mapping |
| `GET/PUT/DELETE` | `/api/mappings/{id}` | Read / update / delete a mapping |
| `GET`  | `/api/jobs` | List sync jobs |
| `POST` | `/api/jobs` | Create a job |
| `GET/PUT/DELETE` | `/api/jobs/{id}` | Read / update / delete a job |
| `POST` | `/api/jobs/{id}/run` | Run a job's simulation, persist a run log |
| `POST` | `/api/preview/{mapping_id}` | Dry-run a mapping against a payload (no persistence) |
| `GET`  | `/api/webhooks` | List webhooks |
| `POST` | `/api/webhooks` | Register a webhook |
| `DELETE` | `/api/webhooks/{id}` | Remove a webhook |
| `POST` | `/api/webhooks/hooks/{path}` | Fire the webhook → runs the bound job |
| `GET`  | `/api/dashboard` | Aggregate job/run statistics and recent runs |
| `GET`  | `/api/health` | Liveness probe |

Full request/response reference with curl examples: [docs/API.md](docs/API.md).
Interactive schemas at `/docs`, `/redoc`, and `/api/openapi.json`.

## Configuration

All settings are environment variables (optionally loaded from a `.env` file
at the project root). Copy `.env.example` to `.env` to override. Full table
with examples: [docs/env-config.md](docs/env-config.md).

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSBRIDGE_DB_PATH` | `<root>/data/nexusbridge.db` | SQLite database file |
| `NEXUSBRIDGE_DATA_DIR` | `<root>/data` | Data directory |
| `NEXUSBRIDGE_FRONTEND_DIR` | `<root>/frontend` | Static web workspace |
| `NEXUSBRIDGE_HOST` | `0.0.0.0` | Bind host |
| `NEXUSBRIDGE_PORT` | `8000` | Bind port |

## Repository layout

```
NexusBridge/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint (wires routers + static)
│   │   ├── config.py          # Settings from env / .env
│   │   ├── database.py        # sqlite3 connection, schema, seed data
│   │   ├── engine.py          # Deterministic transforms + run simulation
│   │   ├── models.py          # Pydantic I/O models + validation
│   │   └── routers/           # connectors, mappings, jobs, preview, webhooks, dashboard
│   ├── tests/                 # pytest suite (22 tests)
│   ├── requirements.txt       # runtime deps
│   ├── requirements-dev.txt   # + test deps
│   └── pyproject.toml         # packaging + pytest config
├── frontend/                  # Vanilla SPA (index.html, styles.css, app.js)
├── docs/                      # This documentation set
├── data/                      # Runtime SQLite DB (gitignored; created on boot)
└── .gitignore
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Running locally](docs/RUNNING.md)
- [API reference](docs/API.md)
- [Features](docs/FEATURES.md)
- [Tech stack](docs/TECH-STACK.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Environment configuration](docs/env-config.md)
- [Playbook crosswalk](docs/PLAYBOOK-CROSSWALK.md)

---

*Reference implementation. No network calls, no stored secrets.*