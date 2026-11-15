"""CRUD endpoints for sync jobs plus the run trigger.

Running a job executes the deterministic local simulation described in
:mod:`app.engine` — no external systems are reached.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..database import JOB_STATUSES, get_db, query_one, row_to_dict
from ..engine import run_job_simulation
from ..models import JobCreate, JobOut, JobUpdate, RunResult

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _validate_job(source_cid: int, target_cid: int, mapping_id: int) -> None:
    """Ensure the job references existing connectors and a mapping."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM connectors WHERE id = ?", (source_cid,)):
            raise HTTPException(422, f"Source connector {source_cid} not found")
        if not query_one(conn, "SELECT id FROM connectors WHERE id = ?", (target_cid,)):
            raise HTTPException(422, f"Target connector {target_cid} not found")
        if not query_one(conn, "SELECT id FROM mappings WHERE id = ?", (mapping_id,)):
            raise HTTPException(422, f"Mapping {mapping_id} not found")


@router.get("", response_model=list[JobOut])
def list_jobs() -> list[dict]:
    """List all jobs."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate) -> dict:
    """Create a sync job."""
    _validate_job(payload.source_connector_id, payload.target_connector_id, payload.mapping_id)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (name, source_connector_id, target_connector_id,"
            " mapping_id, schedule_note, status) VALUES (?,?,?,?,?,?)",
            (payload.name.strip(), payload.source_connector_id,
             payload.target_connector_id, payload.mapping_id,
             payload.schedule_note, payload.status),
        )
        row = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (cur.lastrowid,))
    return row_to_dict(row)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int) -> dict:
    """Fetch a single job."""
    with get_db() as conn:
        row = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(404, "Job not found")
    return row_to_dict(row)


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, payload: JobUpdate) -> dict:
    """Update a job (fields present in the payload are applied)."""
    with get_db() as conn:
        existing = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))
        if not existing:
            raise HTTPException(404, "Job not found")
        data = row_to_dict(existing)
        updates = payload.model_dump(exclude_unset=True)
        merged = {**data, **updates}
        _validate_job(merged["source_connector_id"], merged["target_connector_id"],
                      merged["mapping_id"])
        if merged["status"] not in JOB_STATUSES:
            raise HTTPException(422, f"Invalid status: {merged['status']}")
        conn.execute(
            "UPDATE jobs SET name=?, source_connector_id=?, target_connector_id=?,"
            " mapping_id=?, schedule_note=?, status=? WHERE id=?",
            (merged["name"].strip(), merged["source_connector_id"],
             merged["target_connector_id"], merged["mapping_id"],
             merged["schedule_note"], merged["status"], job_id),
        )
        row = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))
    return row_to_dict(row)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int) -> Response:
    """Delete a job."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM jobs WHERE id = ?", (job_id,)):
            raise HTTPException(404, "Job not found")
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/run", response_model=RunResult)
def run_job(job_id: int) -> dict:
    """Execute the local deterministic simulation for a job.

    Reads the job's connector + mapping, applies the transforms to the canned
    sample payload, persists a run log and returns the transformed batch.
    """
    with get_db() as conn:
        job = query_one(conn, "SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        result = run_job_simulation(job)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return result.model_dump()