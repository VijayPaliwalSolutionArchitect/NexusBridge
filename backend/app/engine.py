"""Deterministic transformation engine and in-memory sync simulation.

No network calls happen anywhere in this module.  Each connector type has a
canned sample payload (list of row dicts) that stands in for the real
remote system.  ``run_job_simulation`` applies a mapping's field rules to
that sample batch and reports rows-in/rows-out plus any per-row errors.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .database import get_db, query_one
from .models import RunResult

# ---------------------------------------------------------------------------
# Sample payloads (deterministic, per connector type)
# ---------------------------------------------------------------------------
SAMPLE_PAYLOADS: dict[str, list[dict]] = {
    "rest": [
        {"Name": "Alice Zhang", "Email": "ALICE@EXAMPLE.COM", "Type": "lead",
         "Region_Code": "NA"},
        {"Name": "Bob Nguyen", "Email": "bob@example.com", "Type": "customer",
         "Region_Code": "APAC"},
    ],
    "api": [
        {"Name": "Carol White", "Email": "CAROL@EXAMPLE.COM", "Type": "partner",
         "Region_Code": "EU"},
        {"Name": "Dave Patel", "Email": "dave@example.com", "Type": "lead",
         "Region_Code": "APAC"},
    ],
    "db": [
        {"Order_No": "ORD-1001", "Status": "paid", "created_on": "2026-11-11T08:00:00Z"},
        {"Order_No": "ORD-1002", "Status": "pending", "created_on": "2026-11-11T09:30:00Z"},
    ],
    "sftp": [
        {"File": "invoices/2026-11.csv", "Rows": "12", "Loaded": "2026-11-11T10:00:00Z"},
    ],
    "queue": [
        {"Order_No": "Q-5001", "Status": "queued", "Priority": "high"},
        {"Order_No": "Q-5002", "Status": "queued", "Priority": "low"},
    ],
}


# ---------------------------------------------------------------------------
# Field transforms
# ---------------------------------------------------------------------------
def _transform_value(transform: str, param: str | None, value: Any) -> Any:
    """Apply a single transform to one source value."""
    if transform in ("direct", ""):
        return value
    if transform == "upper":
        return value.upper() if isinstance(value, str) else value
    if transform == "lower":
        return value.lower() if isinstance(value, str) else value
    if transform == "const":
        return param
    if transform == "concat":
        # Concatenate the source value with the param literal when provided.
        return f"{value}{param}" if param is not None else value
    raise ValueError(f"Unknown transform: {transform}")


def normalize_field(name: str) -> str:
    """Map a raw source key to the field names the transforms expect."""
    return name.strip()


def apply_mapping_to_row(
    mapping_field_rows: list[dict], row: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Apply a mapping's field rules to a single source row.

    Returns ``(output_row, errors)``.  A missing source field or a bad
    transform is recorded as an error; already-mapped target fields are left
    out of ``output_row`` to keep the batch clean.
    """
    output: dict[str, Any] = {}
    errors: list[str] = []

    for rule in mapping_field_rows:
        source_field = rule["source_field"]
        target_field = rule["target_field"]
        transform = rule["transform"]
        param = rule["transform_param"]

        if transform == "const":
            output[target_field] = param
            continue

        if source_field not in row:
            errors.append(f"Missing field: {source_field} (target {target_field})")
            continue

        try:
            output[target_field] = _transform_value(transform, param, row[source_field])
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Transform error on {source_field}: {exc}")

    return output, errors


def _fetch_mapping_fields(mapping_id: int) -> list[dict]:
    """Load every field rule for a mapping, ordered by sort_order."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, mapping_id, source_field, target_field, transform,"
            " transform_param, sort_order FROM mapping_fields"
            " WHERE mapping_id = ? ORDER BY sort_order, id",
            (mapping_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _sample_for_connector(connector_type: str, base_url: str) -> list[dict]:
    """Return the deterministic sample payload for a connector type.

    The action is keyed off the connector type but the sample list is always
    the same regardless of the (fake) base_url, so runs are reproducible.
    """
    return SAMPLE_PAYLOADS.get(connector_type, SAMPLE_PAYLOADS["rest"])


def run_job_simulation(job) -> RunResult:
    """Run a sync job simulation and persist a run log.

    ``job`` must be a dict-like row with keys ``id``, ``source_connector_id``,
    ``target_connector_id`` and ``mapping_id``.
    """
    with get_db() as conn:
        source = query_one(conn, "SELECT * FROM connectors WHERE id = ?",
                          (job["source_connector_id"],))
        target = query_one(conn, "SELECT * FROM connectors WHERE id = ?",
                          (job["target_connector_id"],))
        if not source or not target:
            raise ValueError("Job references a missing source or target connector")
        mapping = query_one(conn, "SELECT * FROM mappings WHERE id = ?",
                            (job["mapping_id"],))
        if not mapping:
            raise ValueError("Job references a missing mapping")

        mapping_field_rows = list(
            conn.execute(
                "SELECT * FROM mapping_fields WHERE mapping_id = ? ORDER BY sort_order, id",
                (job["mapping_id"],),
            )
        )

    rows_in_rows = _sample_for_connector(source["type"], source["base_url"] or "")
    rows_in = len(rows_in_rows)

    output_rows: list[dict[str, Any]] = []
    errors_total: list[str] = []

    for row in rows_in_rows:
        normalized = {normalize_field(k): v for k, v in row.items()}
        out_row, row_errors = apply_mapping_to_row(
            [dict(r) for r in mapping_field_rows], normalized
        )
        if row_errors:
            errors_total.extend(row_errors)
        # Include the row even if partial, but only when it produced output.
        if out_row:
            output_rows.append(out_row)

    status = "failure" if errors_total else "success"
    started = datetime.now(timezone.utc).isoformat()
    finished = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO run_logs (job_id, status, rows_in, rows_out, error,"
            " started_at, finished_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (job["id"], status, rows_in, len(output_rows),
             "; ".join(errors_total) if errors_total else None,
             started, finished),
        )
        log_id = cur.lastrowid
        log_row = query_one(
            conn,
            "SELECT id, job_id, status, rows_in, rows_out, error, started_at,"
            " finished_at FROM run_logs WHERE id = ?",
            (log_id,),
        )

    return RunResult(**dict(log_row), output=output_rows)


# ---------------------------------------------------------------------------
# Verification helper (used by tests and health checks)
# ---------------------------------------------------------------------------
def apply_mapping_to_sample(mapping_id: int) -> RunResult:
    """Run the canned simulation for a mapping (without persisting a log)."""
    with get_db() as conn:
        mapping = query_one(conn, "SELECT * FROM mappings WHERE id = ?", (mapping_id,))
        if not mapping:
            raise ValueError("Mapping not found")
        source = query_one(conn, "SELECT * FROM connectors WHERE id = ?",
                          (mapping["source_connector_id"],))
        mapping_field_rows = list(
            conn.execute(
                "SELECT * FROM mapping_fields WHERE mapping_id = ? ORDER BY sort_order, id",
                (mapping_id,),
            )
        )
    rows = SAMPLE_PAYLOADS.get(source["type"], SAMPLE_PAYLOADS["rest"])
    rules = [dict(r) for r in mapping_field_rows]
    output: list[dict] = []
    for row in rows:
        normalized = {normalize_field(k): v for k, v in row.items()}
        out_row, _errors = apply_mapping_to_row(rules, normalized)
        if out_row:
            output.append(out_row)
    return RunResult(
                id=0, job_id=0, status="success", rows_in=len(rows), rows_out=len(output),
                error=None, started_at="", finished_at="", output=output,
            )