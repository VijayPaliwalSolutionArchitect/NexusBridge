# NexusBridge — Installation

## Prerequisites

- **Python 3.10+** (developed on 3.14)
- **pip** (or `uv`)
- Git (to clone)

## Steps

```bash
# 1. Clone
git clone https://github.com/VijayPaliwalSolutionArchitect/NexusBridge.git
cd NexusBridge/backend

# 2. Virtual environment
python -m venv .venv
source .venv/Scripts/activate        # Windows git-bash
# .venv\Scripts\activate             # Windows cmd
# source .venv/bin/activate          # macOS/Linux

# 3. Install dependencies
pip install -r requirements-dev.txt   # runtime + test deps
# or: pip install -r requirements.txt # runtime only
```

## Verify the install

```bash
python -c "import fastapi, pydantic, uvicorn; print('deps ok')"
```

## First boot (creates + seeds the database)

```bash
uvicorn app.main:app --reload
# → http://127.0.0.1:8000  (workspace)
# → http://127.0.0.1:8000/docs (OpenAPI)
# → http://127.0.0.1:8000/api/health
```

The backend auto-creates `data/nexusbridge.db` and seeds sample connectors,
mappings, jobs, a webhook, and run logs on first boot.

## Run the test suite

```bash
python -m pytest            # expect 22 passed (uses an isolated throwaway DB)
```
