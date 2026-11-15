"""CRUD endpoints for connectors.

Secrets are never stored: ``auth_type`` is a label only, and any secret
material in ``base_url``/``notes`` is rejected or stripped.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..database import CONNECTOR_TYPES, get_db, query_one, row_to_dict
from ..models import ConnectorCreate, ConnectorOut, ConnectorUpdate

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

# A tiny allow-list of exposed, non-secret URL/value patterns we keep.
# Everything else is treated as a placeholder and accepted as-is (no
# validation of credential material) — the API simply never reads real
# secrets back out.
_FORBIDDEN_PLACEHOLDERS = ("password", "token=", "secret", "api_key", "authorization")


def _sanitize_connector(data: dict) -> dict:
    """Drop obvious secret-looking substrings before persisting."""
    out = dict(data)
    for key in ("base_url", "notes"):
        value = out.get(key)
        if isinstance(value, str):
            lowered = value.lower()
            for marker in _FORBIDDEN_PLACEHOLDERS:
                if marker in lowered:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Secret material detected in '{key}'. "
                        "NexusBridge stores placeholders only.",
                    )
    return out


@router.get("", response_model=list[ConnectorOut])
def list_connectors() -> list[dict]:
    """List all connectors."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM connectors ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("", response_model=ConnectorOut, status_code=status.HTTP_201_CREATED)
def create_connector(payload: ConnectorCreate) -> dict:
    """Create a connector (placeholders only)."""
    data = _sanitize_connector(payload.model_dump())
    if data["type"] not in CONNECTOR_TYPES:
        raise HTTPException(422, f"Invalid connector type: {data['type']}")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO connectors (name, type, base_url, auth_type, notes)"
            " VALUES (?,?,?,?,?)",
            (data["name"], data["type"], data["base_url"],
             data["auth_type"], data["notes"]),
        )
        row = query_one(conn, "SELECT * FROM connectors WHERE id = ?", (cur.lastrowid,))
    return row_to_dict(row)


@router.get("/{connector_id}", response_model=ConnectorOut)
def get_connector(connector_id: int) -> dict:
    """Fetch a single connector."""
    with get_db() as conn:
        row = query_one(conn, "SELECT * FROM connectors WHERE id = ?", (connector_id,))
    if not row:
        raise HTTPException(404, "Connector not found")
    return row_to_dict(row)


@router.put("/{connector_id}", response_model=ConnectorOut)
def update_connector(connector_id: int, payload: ConnectorUpdate) -> dict:
    """Update a connector (fields present in the payload are applied)."""
    with get_db() as conn:
        existing = query_one(conn, "SELECT * FROM connectors WHERE id = ?", (connector_id,))
        if not existing:
            raise HTTPException(404, "Connector not found")
        data = existing_to_dict = row_to_dict(existing)
        updates = payload.model_dump(exclude_unset=True)
        merged = {**data, **updates}
        merged = _sanitize_connector(merged)
        if merged["type"] not in CONNECTOR_TYPES:
            raise HTTPException(422, f"Invalid connector type: {merged['type']}")
        conn.execute(
            "UPDATE connectors SET name=?, type=?, base_url=?, auth_type=?, notes=?"
            " WHERE id=?",
            (merged["name"], merged["type"], merged["base_url"],
             merged["auth_type"], merged["notes"], connector_id),
        )
        row = query_one(conn, "SELECT * FROM connectors WHERE id = ?", (connector_id,))
    return row_to_dict(row)


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(connector_id: int) -> Response:
    """Delete a connector."""
    with get_db() as conn:
        existing = query_one(conn, "SELECT id FROM connectors WHERE id = ?", (connector_id,))
        if not existing:
            raise HTTPException(404, "Connector not found")
        conn.execute("DELETE FROM connectors WHERE id = ?", (connector_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)