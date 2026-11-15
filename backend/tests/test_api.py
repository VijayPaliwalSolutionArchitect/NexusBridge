"""End-to-end API tests exercising the CRUD surfaces with the test client."""

from __future__ import annotations


def test_list_seeded_connectors(client) -> None:
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["name"] == "Salesforce CRM"


def test_create_and_fetch_connector(client) -> None:
    payload = {
        "name": "NetSuite API",
        "type": "api",
        "base_url": "https://api.netsuite.example",
        "auth_type": "bearer",
        "notes": "Placeholder connection.",
    }
    created = client.post("/api/connectors", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "NetSuite API"
    cid = body["id"]
    fetched = client.get(f"/api/connectors/{cid}")
    assert fetched.status_code == 200
    assert fetched.json()["type"] == "api"


def test_connector_crud_lifecycle(client) -> None:
    payload = {"name": "Temp", "type": "db", "auth_type": "none"}
    cid = client.post("/api/connectors", json=payload).json()["id"]
    upd = client.put(f"/api/connectors/{cid}", json={"notes": "updated"})
    assert upd.status_code == 200
    assert upd.json()["notes"] == "updated"
    dele = client.delete(f"/api/connectors/{cid}")
    assert dele.status_code == 204
    assert client.get(f"/api/connectors/{cid}").status_code == 404


def test_secret_material_is_rejected(client) -> None:
    resp = client.post(
        "/api/connectors",
        json={
            "name": "Bad",
            "type": "rest",
            "base_url": "https://x.example?token=abc123",
            "auth_type": "none",
        },
    )
    assert resp.status_code == 422


def test_list_mappings_includes_fields(client) -> None:
    resp = client.get("/api/mappings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert all("fields" in m for m in data)
    assert data[0]["name"] == "Customer Sync"


def test_jobs_list_and_run(client) -> None:
    jobs = client.get("/api/jobs").json()
    assert len(jobs) >= 2
    job_id = jobs[0]["id"]
    run = client.post(f"/api/jobs/{job_id}/run")
    assert run.status_code == 200
    body = run.json()
    assert body["rows_in"] == 2
    assert body["rows_out"] == 2
    assert body["status"] in ("success", "failure")
    assert isinstance(body["output"], list)


def test_webhook_triggers_seeded_job(client) -> None:
    resp = client.post("/api/webhooks/hooks/customer-sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("success", "failure")


def test_webhook_create_and_delete(client) -> None:
    job_id = client.get("/api/jobs").json()[0]["id"]
    created = client.post(
        "/api/webhooks", json={"job_id": job_id, "path": "nightly-sync"}
    )
    assert created.status_code == 201
    assert created.json()["path"] == "/hooks/nightly-sync"

    trigger = client.post("/api/webhooks/hooks/nightly-sync")
    assert trigger.status_code == 200

    duplicate = client.post(
        "/api/webhooks", json={"job_id": job_id, "path": "nightly-sync"}
    )
    assert duplicate.status_code == 409

    wid = created.json()["id"]
    assert client.delete(f"/api/webhooks/{wid}").status_code == 204


def test_preview_mapping(client) -> None:
    resp = client.post(
        "/api/preview/1",
        json={"payload": [
            {"Name": "Eve", "Email": "EVE@EXAMPLE.COM", "Type": "lead",
             "Region_Code": "EU"},
            {"Name": "Frank", "Type": "customer", "Region_Code": "US"},
        ]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rows_in"] == 2
    assert body["rows_out"] == 2
    assert body["output"][0]["email"] == "eve@example.com"
    assert body["output"][0]["region"] == "APAC"


def test_dashboard_aggregates(client) -> None:
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_jobs"] >= 2
    assert body["active_jobs"] >= 1
    assert "jobs" in body
    assert "recent_runs" in body
    assert "overall_error_rate" in body


def test_run_missing_job_returns_404(client) -> None:
    assert client.post("/api/jobs/999999/run").status_code == 404