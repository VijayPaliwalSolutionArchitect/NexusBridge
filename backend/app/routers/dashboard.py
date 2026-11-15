"""Dashboard aggregation endpoint.

Computes per-job health stats (total/success/failure runs, rows in/out,
error rate, last run) plus a workspace-level summary.  Powers the
governance/audit view described in the Playbook and the web workspace home
screen.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..database import get_db, query_one
from ..models import DashboardOut, JobStats, RunLogOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard() -> dict:
    """Return aggregate job statistics and the most recent run logs."""
    with get_db() as conn:
        total_jobs = query_one(conn, "SELECT COUNT(*) AS c FROM jobs")["c"]
        active_jobs = query_one(
            conn, "SELECT COUNT(*) AS c FROM jobs WHERE status = 'active'"
        )["c"]
        paused_jobs = total_jobs - active_jobs

        total_runs = query_one(conn, "SELECT COUNT(*) AS c FROM run_logs")["c"]
        total_rows_in = query_one(
            conn, "SELECT COALESCE(SUM(rows_in),0) AS s FROM run_logs"
        )["s"]
        total_rows_out = query_one(
            conn, "SELECT COALESCE(SUM(rows_out),0) AS s FROM run_logs"
        )["s"]
        failure_runs_total = query_one(
            conn, "SELECT COUNT(*) AS c FROM run_logs WHERE status = 'failure'"
        )["c"]

        jobs = conn.execute(
            "SELECT * FROM jobs ORDER BY id"
        ).fetchall()
        recent_runs = conn.execute(
            "SELECT id, job_id, status, rows_in, rows_out, error, started_at,"
            " finished_at FROM run_logs ORDER BY id DESC LIMIT 20"
        ).fetchall()

    overall_error_rate = (failure_runs_total / total_runs) if total_runs else 0.0

    job_stats: list[JobStats] = []
    for job in jobs:
        job_id = job["id"]
        with get_db() as conn:
            logs = conn.execute(
                "SELECT id, job_id, status, rows_in, rows_out, error, started_at,"
                " finished_at FROM run_logs WHERE job_id = ? ORDER BY id",
                (job_id,),
            ).fetchall()
        success_runs = sum(1 for r in logs if r["status"] == "success")
        rows_in = sum(r["rows_in"] for r in logs)
        rows_out = sum(r["rows_out"] for r in logs)
        last = logs[-1] if logs else None
        job_stats.append(
            JobStats(
                job_id=job_id,
                name=job["name"],
                status=job["status"],
                total_runs=len(logs),
                success_runs=success_runs,
                failure_runs=len(logs) - success_runs,
                rows_in=rows_in,
                rows_out=rows_out,
                error_rate=(len(logs) - success_runs) / len(logs) if logs else 0.0,
                last_run_status=last["status"] if last else None,
                last_run_at=last["started_at"] if last else None,
            )
        )

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "paused_jobs": paused_jobs,
        "total_runs": total_runs,
        "total_rows_in": total_rows_in,
        "total_rows_out": total_rows_out,
        "overall_error_rate": round(overall_error_rate, 4),
        "jobs": [js.model_dump() for js in job_stats],
        "recent_runs": [RunLogOut(**dict(r)).model_dump() for r in recent_runs],
    }