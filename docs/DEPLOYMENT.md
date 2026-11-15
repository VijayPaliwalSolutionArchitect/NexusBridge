# NexusBridge — Deployment

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

Playbook deployment path: a single VPS running the app behind Caddy TLS,
optionally orchestrated by Coolify. The app is one stateless process plus one
SQLite file, so deployment is deliberately simple.

---

## 1. Local / dev

```bash
cd backend
source .venv/Scripts/activate        # Windows git-bash; .venv\Scripts\activate in cmd
uvicorn app.main:app --reload --port 8000
```

## 2. Production on a VPS (systemd)

```ini
# /etc/systemd/system/nexusbridge.service
[Unit]
Description=NexusBridge API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/NexusBridge/backend
Environment=NEXUSBRIDGE_DATA_DIR=/var/lib/nexusbridge
Environment=NEXUSBRIDGE_DB_PATH=/var/lib/nexusbridge/nexusbridge.db
Environment=NEXUSBRIDGE_FRONTEND_DIR=/opt/NexusBridge/frontend
Environment=NEXUSBRIDGE_HOST=127.0.0.1
Environment=NEXUSBRIDGE_PORT=8000
ExecStart=/opt/NexusBridge/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nexusbridge
sudo systemctl status nexusbridge
```

Fresh-VPS setup:

```bash
sudo apt update && sudo apt install -y python3.14 python3.14-venv git
sudo mkdir -p /opt/NexusBridge /var/lib/nexusbridge
sudo git clone <repo-url> /opt/NexusBridge
cd /opt/NexusBridge/backend
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 3. TLS reverse proxy (Caddy)

```
nexus.shivamitcs.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy provisions and renews the Let's Encrypt certificate automatically.
(nginx equivalent: `location / { proxy_pass http://127.0.0.1:8000; }`)

## 4. Docker (optional)

```dockerfile
# Dockerfile at repo root
FROM python:3.14-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
ENV NEXUSBRIDGE_FRONTEND_DIR=/app/frontend
ENV NEXUSBRIDGE_DATA_DIR=/data
ENV NEXUSBRIDGE_DB_PATH=/data/nexusbridge.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t nexusbridge .
docker run -p 8000:8000 -v nexusbridge-data:/data nexusbridge
```

```yaml
# docker-compose.yml
services:
  nexusbridge:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/data
```

## 5. Coolify (per playbook)

1. New **Docker Compose** resource in Coolify pointing at this repo.
2. Add domain `nexus.shivamitcs.com` — Coolify provisions TLS automatically.
3. Set env vars in the Coolify panel from [env-config.md](env-config.md)
   (`NEXUSBRIDGE_DB_PATH`, `NEXUSBRIDGE_PORT`, …). **This reference build has
   no secrets**; a production derivative would keep Entra ID client secrets in
   Coolify's secret store, never in the repo.
4. Deploy; verify `https://nexus.shivamitcs.com/api/health` returns `ok`.

## 6. Backups

SQLite is a single file — snapshot it nightly (VACUUM INTO gives a consistent
copy of a live DB):

```bash
sqlite3 /var/lib/nexusbridge/nexusbridge.db \
  "VACUUM INTO '/backups/nexusbridge-$(date +%F).db'"
# plain copy also works when the app is idle: cp .../nexusbridge.db /backups/
```

Code + docs live in git; `data/` and `.env` are git-ignored by design.

## 7. Scaling & hardening notes

- The API is stateless apart from SQLite; run multiple uvicorn workers behind
  the reverse proxy for CPU-bound work.
- SQLite allows one writer at a time — fine at reference data volumes. For
  multi-node, swap the `database.py` layer to PostgreSQL; nothing else changes.
- The reference implementation makes **no outbound network calls and stores no
  secrets**, so there is no credential-rotation surface. A production M365/D365
  version would add Entra ID OAuth (delegated Graph permissions) with
  `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` kept only in the platform secret
  store.
