# NexusBridge — Environment Configuration

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

All settings are loaded by `backend/app/config.py` from environment variables,
with an optional `.env` file at the **project root** (copy `.env.example`).
The loader is a small stdlib parser — `KEY=value` lines, `#` comments, blank
lines; no dependency on `python-dotenv`.

**No secrets exist in this project.** The app stores no API keys, tokens, or
passwords — `auth_type` on connectors is a label only. Never put real
credentials in `.env`; if a future version needs them, keep them in a platform
secret store and reference them here as placeholders.

## Variables

| Variable | Default | Description | Example |
|---|---|---|---|
| `NEXUSBRIDGE_DATA_DIR` | `<project root>/data` | Directory for runtime data (DB file). Created on boot if missing. | `C:/Vijay-Projects/NexusBridge/data` |
| `NEXUSBRIDGE_DB_PATH` | `<NEXUSBRIDGE_DATA_DIR>/nexusbridge.db` | SQLite database file. Use `:memory:` for an ephemeral DB (tests do this). | `/var/lib/nexusbridge/nexusbridge.db` |
| `NEXUSBRIDGE_FRONTEND_DIR` | `<project root>/frontend` | Directory of the static web workspace mounted at `/`. If missing, the API still serves; `/` returns 404. | `/opt/NexusBridge/frontend` |
| `NEXUSBRIDGE_HOST` | `0.0.0.0` | Bind host passed to uvicorn. Use `127.0.0.1` when running behind a reverse proxy. | `127.0.0.1` |
| `NEXUSBRIDGE_PORT` | `8000` | Bind port passed to uvicorn. | `8000` |

## `.env` example

```ini
# NexusBridge local configuration (all values optional — these are the defaults)
NEXUSBRIDGE_DATA_DIR=./data
NEXUSBRIDGE_DB_PATH=./data/nexusbridge.db
NEXUSBRIDGE_FRONTEND_DIR=./frontend
NEXUSBRIDGE_HOST=0.0.0.0
NEXUSBRIDGE_PORT=8000
```

## How it loads

1. Process environment wins.
2. Otherwise, `config.py` reads `<project root>/.env` (resolved relative to
   `config.py`'s location: `Path(__file__).resolve().parents[2] / ".env"`).
3. Otherwise, the defaults above apply.

## Precedence example

```bash
# Override just the port without editing .env:
NEXUSBRIDGE_PORT=8001 uvicorn app.main:app
```

See [RUNNING.md](RUNNING.md) §3 and [DEPLOYMENT.md](DEPLOYMENT.md) for how these
are used in production (systemd `Environment=` lines, Docker `environment:`,
Coolify env panel).
