"""Pydantic request/response models for the NexusBridge API.

These match the SQLite schema but only expose non-secret, serialisable
fields.  Auth-related values are *always* placeholders (see the validation
in :mod:`app.security`).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .database import AUTH_TYPES, CONNECTOR_TYPES, JOB_STATUSES, TRANSFORM_TYPES


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
class ConnectorBase(BaseModel):
    """Shared connector fields."""

    name: str = Field(..., min_length=1, max_length=200)
    type: Literal["rest", "api", "db", "sftp", "queue"]
    base_url: Optional[str] = Field(None, max_length=2000)
    auth_type: Literal["none", "bearer", "basic"] = "none"
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def _strip_url(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ConnectorCreate(ConnectorBase):
    """Payload for creating a connector."""

    @field_validator("auth_type")
    @classmethod
    def _auth_placeholder_only(cls, v: str) -> str:
        if v not in AUTH_TYPES:
            raise ValueError(f"auth_type must be one of {list(AUTH_TYPES)}")
        return v


class ConnectorUpdate(BaseModel):
    """Optional partial update for a connector."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[Literal["rest", "api", "db", "sftp", "queue"]] = None
    base_url: Optional[str] = Field(None, max_length=2000)
    auth_type: Optional[str] = None
    notes: Optional[str] = None


class ConnectorOut(ConnectorBase):
    """Connector as returned to the client."""

    id: int
    created_at: str


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
class MappingFieldIn(BaseModel):
    """A single source->target field mapping rule."""

    source_field: str = Field(..., min_length=1, max_length=500)
    target_field: str = Field(..., min_length=1, max_length=500)
    transform: Literal["direct", "upper", "lower", "concat", "const"] = "direct"
    transform_param: Optional[str] = None


class MappingFieldOut(MappingFieldIn):
    """A mapping field with its database identity."""

    id: int
    sort_order: int = 0


class MappingBase(BaseModel):
    """Shared mapping fields."""

    name: str = Field(..., min_length=1, max_length=200)
    source_connector_id: int = Field(..., gt=0)
    target_connector_id: int = Field(..., gt=0)
    notes: Optional[str] = None


class MappingCreate(MappingBase):
    """Payload for creating a mapping with its fields."""

    fields: list[MappingFieldIn] = Field(default_factory=list)


class MappingUpdate(BaseModel):
    """Optional partial update for a mapping (fields replaced wholesale)."""

    name: Optional[str] = None
    source_connector_id: Optional[int] = Field(None, gt=0)
    target_connector_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = None
    fields: Optional[list[MappingFieldIn]] = None


class MappingOut(MappingBase):
    """Mapping as returned to the client, including its rules."""

    id: int
    created_at: str
    fields: list[MappingFieldOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
class JobBase(BaseModel):
    """Shared job fields."""

    name: str = Field(..., min_length=1, max_length=200)
    source_connector_id: int = Field(..., gt=0)
    target_connector_id: int = Field(..., gt=0)
    mapping_id: int = Field(..., gt=0)
    schedule_note: Optional[str] = None
    status: Literal["active", "paused"] = "active"


class JobCreate(JobBase):
    """Payload for creating a job."""


class JobUpdate(BaseModel):
    """Optional partial update for a job."""

    name: Optional[str] = None
    source_connector_id: Optional[int] = Field(None, gt=0)
    target_connector_id: Optional[int] = Field(None, gt=0)
    mapping_id: Optional[int] = Field(None, gt=0)
    schedule_note: Optional[str] = None
    status: Optional[str] = None


class JobOut(JobBase):
    """Job as returned to the client."""

    id: int
    created_at: str


# ---------------------------------------------------------------------------
# Run logs
# ---------------------------------------------------------------------------
class RunLogOut(BaseModel):
    """A single run-log record."""

    id: int
    job_id: int
    status: Literal["success", "failure"]
    rows_in: int
    rows_out: int
    error: Optional[str] = None
    started_at: str
    finished_at: str


class RunResult(RunLogOut):
    """Run-log record plus the transformed output batch."""

    output: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
class WebhookCreate(BaseModel):
    """Payload for registering a webhook trigger on a job."""

    job_id: int = Field(..., gt=0)
    path: str = Field(..., min_length=1, max_length=500)
    method: Literal["POST", "PUT"] = "POST"
    active: bool = True


class WebhookOut(BaseModel):
    """Webhook as returned to the client."""

    id: int
    job_id: int
    path: str
    method: str
    active: bool
    created_at: str


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
class PreviewRequest(BaseModel):
    """Payload for transform preview."""

    mapping_id: int = Field(..., gt=0)
    payload: dict


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class JobStats(BaseModel):
    """Aggregate stats for one job across its run logs."""

    job_id: int
    name: str
    status: str
    total_runs: int
    success_runs: int
    failure_runs: int
    rows_in: int
    rows_out: int
    error_rate: float
    last_run_status: Optional[str] = None
    last_run_at: Optional[str] = None


class DashboardOut(BaseModel):
    """Dashboard summary for all jobs."""

    total_jobs: int
    active_jobs: int
    paused_jobs: int
    total_runs: int
    total_rows_in: int
    total_rows_out: int
    overall_error_rate: float
    jobs: list[JobStats]
    recent_runs: list[RunLogOut]