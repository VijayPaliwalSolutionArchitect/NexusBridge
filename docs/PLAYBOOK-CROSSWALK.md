# NexusBridge — Playbook Crosswalk

> Version: v0.1 · 15-11-26 · Author: SHIVAM ITCS (JARVIS)

Maps every section of the NexusBridge playbook chapter
(`playbook_chapters/NexusBridge.txt`) to what is actually implemented in the
code. Status: ✅ implemented · ◐ partial · ◻ planned.

## 1. Project Snapshot

| Playbook requirement | Implementation |
|---|---|
| What it is: data integration & orchestration workspace for M365/D365 | ✅ `README.md` — NexusBridge as the control plane; connectors/mappings/jobs/webhooks model |
| Who it's for: ops teams, IT consultants, system integrators | ✅ README "Who is it for" |
| One-line pitch | ✅ README tagline |
| Hero-project framing for portfolio | ✅ README portfolio section; this crosswalk |

## 2. The Demand (why it exists)

| Playbook point | Where addressed |
|---|---|
| Orgs drown in siloed SaaS data; spreadsheets/emails as integration layer | ✅ README "The problem"; FEATURES.md |
| Need one governed place to map, preview, run, and audit data flows | ✅ Mapping studio + preview + run logs + dashboard |
| Compliance/auditability (who changed what, when) | ✅ `run_logs` audit trail + `/api/dashboard` error rates |

## 3. Architecture Layers

| Layer (playbook) | Code |
|---|---|
| Presentation (web workspace) | ✅ `frontend/` SPA mounted at `/` (`main.py` `StaticFiles`) |
| API layer | ✅ FastAPI routers in `backend/app/routers/` (`connectors`, `mappings`, `preview`, `jobs`, `webhooks`, `dashboard`) |
| Domain/transform engine | ✅ `engine.py` (`run_preview`, `run_job` with `_transform_value`: direct/upper/lower/concat/const) |
| Persistence | ✅ `database.py` — SQLite schema + CRUD helpers + seed |
| Config | ✅ `config.py` — env-driven settings, stdlib `.env` loader |
| Models/validation | ✅ `models.py` — Pydantic v2 schemas |

See [ARCHITECTURE.md](ARCHITECTURE.md) for diagrams.

## 4. PRD / MoSCoW

| Priority | Feature | Status |
|---|---|---|
| Must | Connector registry CRUD | ✅ |
| Must | Field mapping with transforms | ✅ |
| Must | Preview/dry-run without side effects | ✅ |
| Must | Job run + audit log | ✅ |
| Must | Webhook trigger | ✅ |
| Must | Dashboard stats | ✅ |
| Should | Web UI workspace | ✅ (vanilla SPA, no build) |
| Should | Health endpoint + OpenAPI docs | ✅ (`/api/health`, `/docs`) |
| Could | Real scheduler (cron) | ◻ `schedule_note` only |
| Could | Live HTTP fetch from connectors | ◻ simulated payloads |
| Won't (this phase) | Auth/RBAC, multi-tenant, real secrets | ◻ documented as out of scope |

## 5. Functional Requirements (FRs)

| FR | Endpoint / code | Status |
|---|---|---|
| FR-1 Create/read/update/delete connectors | `routers/connectors.py` | ✅ |
| FR-2 Define mappings with ordered field rules | `routers/mappings.py`, `models.MappingCreate` | ✅ |
| FR-3 Preview a mapping against arbitrary payload | `POST /api/preview/{id}` | ✅ |
| FR-4 Run a job and persist a run log | `POST /api/jobs/{id}/run`, `run_logs` | ✅ |
| FR-5 Trigger jobs via webhooks | `routers/webhooks.py` | ✅ |
| FR-6 Aggregate dashboard stats | `GET /api/dashboard` | ✅ |
| FR-7 Liveness probe | `GET /api/health` | ✅ |

Full request/response examples: [API.md](API.md).

## 6. KPIs

| KPI (playbook) | How measured in code |
|---|---|
| Mapping accuracy | `PreviewResponse.errors` per row; run-log `error` field |
| Run success rate / error rate | `/api/dashboard` → `overall_error_rate`, per-job `error_rate` |
| Throughput | `rows_in` / `rows_out` per run + totals on dashboard |
| Adoption | connectors/jobs/webhooks counts on dashboard |

## 7. Work Breakdown (what was built)

1. Backend skeleton: `config.py`, `database.py` (schema + seed), `models.py`
2. Engine: `engine.py` (transforms, preview, job run)
3. Routers: connectors → mappings → preview → jobs → webhooks → dashboard
4. App wiring + static frontend mount: `main.py`
5. Frontend SPA: `frontend/` (dashboard/connectors/mappings/jobs/webhooks tabs)
6. Tests: `backend/tests/` (22 tests — engine unit + API integration)
7. Docs: this `docs/` set + README + `.env.example`

## 8. Deliverables

| Deliverable | Location |
|---|---|
| Runnable backend | `backend/app/` + `backend/tests/` |
| Web workspace | `frontend/` |
| API contract | `/docs`, `/redoc`, `/api/openapi.json`, `docs/API.md` |
| Deployment path | `docs/DEPLOYMENT.md` (systemd, Docker, Coolify, Caddy, backups) |
| Portfolio docs | `README.md`, `docs/PLAYBOOK-CROSSWALK.md` (this file) |

## 9. Benefits

- One governed place for integration definitions (no more spreadsheet mappings).
- Safe experimentation via side-effect-free preview.
- Auditability: every run logged with rows in/out and errors.
- Zero-ops local run: one process + one SQLite file.

## 10. Deployment steps

Covered in [DEPLOYMENT.md](DEPLOYMENT.md): local dev, VPS + systemd, Caddy TLS,
Docker/Compose, Coolify resource, nightly SQLite backup. ✅ documented; ◐
production hardening (Entra ID OAuth) is planned.

## 11. Portfolio angle

- Demonstrates: API design, data modeling, a real transform engine, audit
  logging, testing (22 tests), and doc discipline.
- Talking points: "mappings as data, preview before you run, every run logged" —
  the same principles as enterprise iPaaS tools (n8n/Power Automate) at
  reference scale.
