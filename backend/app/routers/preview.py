"""Transform preview endpoint.

Lets a user dry-run a mapping's field rules against an arbitrary payload
*without* persisting a run log.  This is the "what will this job produce?"
sanity check used by the web workspace before a mapping is activated.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..database import get_db, query_one
from ..engine import apply_mapping_to_row, normalize_field

router = APIRouter(prefix="/api/preview", tags=["preview"])


class PreviewRequestItem(BaseModel):
    """A sample source batch to dry-run against a mapping."""

    payload: list[dict[str, Any]] = Field(..., min_length=1)


class PreviewResponse(BaseModel):
    """Result of a transform preview."""

    mapping_id: int
    mapping_name: str
    rows_in: int = Field(..., ge=0)
    rows_out: int
    errors: list[str] = Field(default_factory=list)
    output: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/{mapping_id}", response_model=PreviewResponse)
def preview_mapping(mapping_id: int, item: PreviewRequestItem) -> PreviewResponse:
    """Apply a mapping's field rules to a sample batch of source rows."""
    with get_db() as conn:
        mapping = query_one(conn, "SELECT * FROM mappings WHERE id = ?", (mapping_id,))
        if not mapping:
            raise HTTPException(404, "Mapping not found")
        fields = conn.execute(
            "SELECT * FROM mapping_fields WHERE mapping_id = ? ORDER BY sort_order, id",
            (mapping_id,),
        ).fetchall()

    output: list[dict[str, Any]] = []
    all_errors: list[str] = []
    for row in item.payload:
        normalized = {normalize_field(k): v for k, v in row.items()}
        out_row, row_errors = apply_mapping_to_row(
            [dict(f) for f in fields], normalized
        )
        all_errors.extend(row_errors)
        if out_row:
            output.append(out_row)

    return PreviewResponse(
        mapping_id=mapping_id,
        mapping_name=mapping["name"],
        rows_in=len(item.payload),
        rows_out=len(output),
        errors=all_errors,
        output=output,
    )