# NexusBridge — Installation

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

Step-by-step local setup. The whole system is one Python process plus a static
folder — **no database server, no Docker, no external services** are required
for local development.

---

## 1. Prerequisites

| Requirement | Version | Check command |
|---|---|---|
| Python | ≥ 3.11 (developed on 3.14; `pyproject.toml` declares `requires-python = ">=3.11"`) | `python --version` |
| pip | bundled with Python | `python -m pip --version` |
| Git | any | `git --version` |
| OS | Windows / macOS / Linux | — |

No external services are needed: the transformation engine is deterministic
and offline, and SQLite ships with the Python standard library.

## 2. Get the code

```bash
cd C:/Vijay-Projects                 # Windows (git-bash)
cd NexusBridge                       # project root
```

## 3. Create a virtual environment (inside `backend/`)

```bash
cd backend
python -m venv .venv

# Activate the venv:
source .venv/Scripts/activate        # Windows (git-bash / MSYS)
# .venv\Scripts\activate             # Windows (cmd.exe)
# source .venv/bin/activate          # macOS / Linux
```

`.venv/`, `venv/`, `env/` are all git-ignored — never commit them.

## 4. Install dependencies

```bash
# Runtime only:
pip install -r requirements.txt

# Runtime + test tools (recommended):
pip install -r requirements-dev.txt
```

| Package | Constraint | Purpose |
|---|---|---|
| `fastapi` | ≥ 0.110 | Web framework, routing, automatic OpenAPI |
| `uvicorn[standard]` | ≥ 0.29 | ASGI server (with `uvloop`/`httptools` extras) |
| `pydantic` | ≥ 2.6 | Request/response validation (Pydantic v2) |
| `pytest` | ≥ 8.0 (dev) | Test runner |
| `httpx` | ≥ 0.27 (dev) | `TestClient` for API tests |

Alternatively, install the backend as a package (uses `pyproject.toml`):

```bash
pip install -e ".[dev]"     # from backend/
```

## 5. Configure environment (optional)

All settings have working defaults. To customize, copy the template and edit:

```bash
cp ../.env.example ../.env        # .env lives at the project root
```

`app/config.py` loads `.env` from the project root at import time with a small
stdlib-only parser (no `python-dotenv` dependency). See
[env-config.md](env-config.md) for every variable.

## 6. Database initialization (automatic)

Nothing to run manually. `app/main.py` calls `init_db()` at import time, which:

1. creates the data directory (`data/` by default),
2. creates `data/nexusbridge.db` (SQLite),
3. creates the schema with `CREATE TABLE IF NOT EXISTS …` (`connectors`,
   `mappings`, `mapping_fields`, `jobs`, `run_logs`, `webhooks`),
4. seeds sample connectors, mappings, field rules, jobs, a webhook, and run
   logs — guarded by a row-count check so restarts never duplicate data.

To reset to a pristine seeded state:

```bash
rm -f ../data/nexusbridge.db      # recreated + reseeded on next boot
```

(`data/` and `*.db` are git-ignored.)

## 7. Verify the install

```bash
# From backend/, venv active:
uvicorn app.main:app --reload

# In another terminal:
curl http://127.0.0.1:8000/api/health
# -> {"service":"nexusbridge","version":"1.0.0","status":"ok"}

# Test suite (uses an isolated throwaway DB, never data/nexusbridge.db):
python -m pytest          # expect: 22 passed
```

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | venv not activated | `source .venv/Scripts/activate` |
| `address already in use` on port 8000 | another process bound to 8000 | `NEXUSBRIDGE_PORT=8001 uvicorn app.main:app` |
| Frontend 404s at `/` | `frontend/` missing or wrong dir | check `NEXUSBRIDGE_FRONTEND_DIR`; the API still works without it |
| Stale/odd data after code changes | old DB file | delete `data/nexusbridge.db` and restart |
| `pytest` not found | installed runtime-only deps | `pip install -r requirements-dev.txt` |
| Tests fail on collection | wrong working directory | run pytest from `backend/` (`pyproject.toml` sets `testpaths = ["tests"]`) |

Next: [RUNNING.md](RUNNING.md) for start modes, endpoints and a curl walkthrough.
