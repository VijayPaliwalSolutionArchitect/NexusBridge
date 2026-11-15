"""CRUD endpoints for field mappings.

Each mapping is defined against source/target connector IDs and carries an
ordered list of field rules (source_field -> target_field with a transform).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..database import TRANSFORM_TYPES, get_db, query_one, row_to_dict
from ..models import MappingCreate, MappingOut, MappingUpdate

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


def _serialize_mapping(row: dict) -> dict:
    """Attach the mapping's field rules to a mapping row."""
    out = dict(row)
    with get_db() as conn:
        fields = conn.execute(
            "SELECT id, mapping_id, source_field, target_field, transform,"
            " transform_param, sort_order FROM mapping_fields"
            " WHERE mapping_id = ? ORDER BY sort_order, id",
            (row["id"],),
        ).fetchall()
    out["fields"] = [dict(f) for f in fields]
    return out


def _validate_mapping(source_cid: int, target_cid: int) -> None:
    """Ensure referenced connectors exist (foreign-key sanity for the API)."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM connectors WHERE id = ?", (source_cid,)):
            raise HTTPException(422, f"Source connector {source_cid} not found")
        if not query_one(conn, "SELECT id FROM connectors WHERE id = ?", (target_cid,)):
            raise HTTPException(422, f"Target connector {target_cid} not found")


def _replace_fields(conn, mapping_id: int, fields: list[dict]) -> None:
    """Replace a mapping's field rules (delete + insert)."""
    conn.execute("DELETE FROM mapping_fields WHERE mapping_id = ?", (mapping_id,))
    for i, f in enumerate(fields):
        if f["transform"] not in TRANSFORM_TYPES:
            raise HTTPException(422, f"Invalid transform: {f['transform']}")
        conn.execute(
            "INSERT INTO mapping_fields (mapping_id, source_field, target_field,"
            " transform, transform_param, sort_order) VALUES (?,?,?,?,?,?)",
            (mapping_id, f["source_field"], f["target_field"],
             f["transform"], f.get("transform_param"), i),
        )


@router.get("", response_model=list[MappingOut])
def list_mappings() -> list[dict]:
    """List all mappings with their field rules."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM mappings ORDER BY id").fetchall()
    return [_serialize_mapping(row_to_dict(r)) for r in rows]


@router.post("", response_model=MappingOut, status_code=status.HTTP_201_CREATED)
def create_mapping(payload: MappingCreate) -> dict:
    """Create a mapping and its field rules."""
    _validate_mapping(payload.source_connector_id, payload.target_connector_id)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO mappings (name, source_connector_id, target_connector_id, notes)"
            " VALUES (?,?,?,?)",
            (payload.name.strip(), payload.source_connector_id,
             payload.target_connector_id, payload.notes),
        )
        mapping_id = cur.lastrowid
        _replace_fields(conn, mapping_id,
                        [f.model_dump() for f in payload.fields])
        row = row_to_dict(query_one(conn, "SELECT * FROM mappings WHERE id = ?",
                                    (mapping_id,)))
    return _serialize_mapping(row)


@router.get("/{mapping_id}", response_model=MappingOut)
def get_mapping(mapping_id: int) -> dict:
    """Fetch a single mapping with its rules."""
    with get_db() as conn:
        row = query_one(conn, "SELECT * FROM mappings WHERE id = ?", (mapping_id,))
    if not row:
        raise HTTPException(404, "Mapping not found")
    return _serialize_mapping(row_to_dict(row))


@router.put("/{mapping_id}", response_model=MappingOut)
def update_mapping(mapping_id: int, payload: MappingUpdate) -> dict:
    """Update a mapping; field rules are replaced wholesale if provided."""
    with get_db() as conn:
        existing = query_one(conn, "SELECT * FROM mappings WHERE id = ?", (mapping_id,))
        if not existing:
            raise HTTPException(404, "Mapping not found")
        data = row_to_dict(existing)
        updates = payload.model_dump(exclude_unset=True)
        merged = {**data, **updates}
        source_cid = merged["source_connector_id"]
        target_cid = merged["target_connector_id"]
        _validate_mapping(source_cid, target_cid)
        conn.execute(
            "UPDATE mappings SET name=?, source_connector_id=?, target_connector_id=?,"
            " notes=? WHERE id=?",
            (merged["name"].strip(), source_cid, target_cid, merged["notes"],
             mapping_id),
        )
        if payload.fields is not None:
            _replace_fields(conn, mapping_id, [f.model_dump() for f in payload.fields])
        row = row_to_dict(query_one(conn, "SELECT * FROM mappings WHERE id = ?",
                                    (mapping_id,)))
    return _serialize_mapping(row)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(mapping_id: int) -> Response:
    """Delete a mapping and its field rules."""
    with get_db() as conn:
        if not query_one(conn, "SELECT id FROM mappings WHERE id = ?", (mapping_id,)):
            raise HTTPException(404, "Mapping not found")
        conn.execute("DELETE FROM mapping_fields WHERE mapping_id = ?", (mapping_id,))
        conn.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)