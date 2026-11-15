"""Unit tests for the deterministic transformation engine.

The engine is pure local logic (no network), so these tests are fast and
repeatable.  They lock down the field transforms, the mapping/row behaviour
and the seeded end-to-end simulation.
"""

from __future__ import annotations

from app.database import get_db, query_one
from app.engine import (
    apply_mapping_to_row,
    apply_mapping_to_sample,
    normalize_field,
    run_job_simulation,
    _transform_value,
)


def test_seed_data_exists() -> None:
    """The database seeds connectors, mappings, field rules and a webhook.

    Uses ``>=`` guards because earlier API tests in the same session may have
    created additional rows in the shared isolated database.
    """
    with get_db() as conn:
        assert query_one(conn, "SELECT COUNT(*) AS c FROM connectors")["c"] >= 3
        assert query_one(conn, "SELECT COUNT(*) AS c FROM mappings")["c"] >= 2
        assert query_one(conn, "SELECT COUNT(*) AS c FROM mapping_fields")["c"] >= 6
        assert query_one(conn, "SELECT COUNT(*) AS c FROM jobs")["c"] >= 2
        assert query_one(conn, "SELECT COUNT(*) AS c FROM webhooks")["c"] >= 1


def test_normalize_field_strips_whitespace() -> None:
    assert normalize_field("  Name  ") == "Name"


def test_transform_value_cases() -> None:
    assert _transform_value("upper", None, "lead") == "LEAD"
    assert _transform_value("lower", None, "SALES") == "sales"
    assert _transform_value("const", "APAC", "anything") == "APAC"
    assert _transform_value("direct", None, {"x": 1}) == {"x": 1}
    assert _transform_value("concat", "-SUF", "abc") == "abc-SUF"


def test_transform_upper_keeps_non_strings() -> None:
    assert _transform_value("upper", None, 1234) == 1234


def test_apply_mapping_to_row_reports_missing_field() -> None:
    rules = [{"source_field": "Email", "target_field": "email",
              "transform": "lower", "transform_param": None}]
    out, errors = apply_mapping_to_row(rules, {})
    assert out == {}
    assert len(errors) == 1
    assert "Missing field: Email" in errors[0]


def test_apply_mapping_to_sample_on_seeded_mapping() -> None:
    result = apply_mapping_to_sample(1)
    # Customer Sync maps CRM contacts -> warehouse. Two sample rows expected.
    # Preview is local and never persisted, so status is the neutral "success".
    assert result.status == "success"
    assert result.rows_in == 2
    assert result.rows_out == 2
    assert result.output[0]["email"] == "alice@example.com"  # lower-cased
    assert result.output[0]["region"] == "APAC"              # const transform


def test_run_job_simulation_persists_log() -> None:
    with get_db() as conn:
        job = query_one(conn, "SELECT * FROM jobs WHERE id = 1")
    with get_db() as conn:
        before = query_one(
            conn, "SELECT COUNT(*) AS c FROM run_logs WHERE job_id = 1"
        )["c"]
    result = run_job_simulation(job)
    with get_db() as conn:
        after = query_one(
            conn, "SELECT COUNT(*) AS c FROM run_logs WHERE job_id = 1"
        )["c"]
    assert after == before + 1
    assert result.rows_in == 2
    assert result.rows_out == 2
    assert result.status == "success"