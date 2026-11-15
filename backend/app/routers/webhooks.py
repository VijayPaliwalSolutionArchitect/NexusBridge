"""Webhook trigger endpoints.

A webhook is a named URL path bound to a job.  The high-level causal chain
in the Playbook — *"n8n executes write-back flows"* — is represented here by
a local, deterministic equivalent: an HTTP ``POST`` to a webhook path runs
the bound job's simulation through :mod:`app.engine` and persists a run log.

Seeding creates one webhook at ``/hooks/customer-sync`` bound to the
Customer Sync job so there is a working hook out of the box.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..database import get_db, query_one, row_to_dict
from ..engine import run_job_simulation
from ..models import RunResult, WebhookCreate, WebhookOut

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookOut])
def list_webhooks() -> list[dict]:
    """List every registered webhook."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM webhooks ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", response_model=WebhookOut, status_code=status.HTTP_201_CREATED)
def create_webhook(payload: WebhookCreate) -> dict:
    """Register a new webhook bound to an existing job."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM jobs WHERE id = ?", (payload.job_id,)):
            raise HTTPException(422, f"Job {payload.job_id} not found")
        # Every webhook lives under /hooks/<name> so a POST to
        # /api/webhooks/hooks/<name> matches the stored path.
        path = payload.path if payload.path.startswith("/hooks/") else (
            "/hooks/" + payload.path.lstrip("/")
        )
        existing = query_one(conn, "SELECT id FROM webhooks WHERE path = ?", (path,))
        if existing:
            raise HTTPException(409, f"Webhook path already registered: {path}")
        cur = conn.execute(
            "INSERT INTO webhooks (job_id, path, method, active) VALUES (?,?,?,?)",
            (payload.job_id, path, payload.method, int(payload.active)),
        )
        row = query_one(conn, "SELECT * FROM webhooks WHERE id = ?", (cur.lastrowid,))
    return row_to_dict(row)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int) -> Response:
    """Remove a webhook."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM webhooks WHERE id = ?", (webhook_id,)):
            raise HTTPException(404, "Webhook not found")
        conn.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/hooks/{path:path}", response_model=RunResult)
def trigger_webhook(path: str) -> dict:
    """Run the job bound to a webhook path (write-back flow trigger).

    This mirrors the path a job receives from an external system: a call to
    ``/api/webhooks/hooks/<path>`` runs the bound job's simulation.  Inactive
    webhooks are still matched but the job is paused unless active.
    """
    with get_db() as conn:
        row = query_one(
            conn,
            "SELECT * FROM webhooks WHERE path = ? AND active = 1",
            (f"/hooks/{path}",),
        )
        if not row:
            raise HTTPException(404, "No active webhook found for this path")
        job = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (row["job_id"],))
    if not job:
        raise HTTPException(404, "Webhook points to a missing job")
    try:
        result = run_job_simulation(job)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return result.model_dump()