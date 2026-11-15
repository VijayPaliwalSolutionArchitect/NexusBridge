# NexusBridge — Deployment

## Local / dev

```bash
uvicorn app.main:app --reload --port 8000
```

## Production (single VPS)

```bash
# systemd unit sketch
[Service]
WorkingDirectory=/opt/NexusBridge/backend
Environment=NEXUSBRIDGE_DB_PATH=/var/lib/nexusbridge/nexusbridge.db
Environment=NEXUSBRIDGE_HOST=127.0.0.1
Environment=NEXUSBRIDGE_PORT=8000
ExecStart=/opt/NexusBridge/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

Put **Caddy** or **nginx** in front for TLS:

```
nexus.shivamitcs.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Docker (optional)

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Coolify (per playbook)

Deploy the compose that runs the FastAPI service behind a Caddy site at
`nexus.shivamitcs.com`. Set the env vars from `docs/env-config.md` in the
Coolify environment panel.

## Backups

SQLite is a single file — back up `data/nexusbridge.db` nightly:

```bash
cp /var/lib/nexusbridge/nexusbridge.db /backups/nexusbridge-$(date +%F).db
```

## Scaling notes

- Stateless API: run multiple uvicorn workers behind a load balancer.
- For multi-node, move SQLite → Postgres (the `database.py` layer is the only
  place to change).
