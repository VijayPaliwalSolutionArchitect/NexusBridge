# NexusBridge — API Reference

Base URL: `http://127.0.0.1:8000`. Interactive docs at `/docs` and `/redoc`.

## Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness probe → `{status, app, version, database}` |

## Connectors

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/connectors` | List all connectors |
| `POST` | `/api/connectors` | Create a connector `{name, type, base_url?, auth_type?, notes?}` |
| `GET` | `/api/connectors/{id}` | Read one connector |
| `PUT` | `/api/connectors/{id}` | Update a connector |
| `DELETE` | `/api/connectors/{id}` | Delete a connector |

`type` ∈ `rest | api | db | sftp | queue`; `auth_type` ∈ `none | bearer | basic`.

## Mappings

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/mappings` | List mappings (with field rules) |
| `POST` | `/api/mappings` | Create a mapping `{name, source_connector_id, target_connector_id, fields:[{source_field,target_field,transform,transform_param?,sort_order?}]}` |
| `GET` | `/api/mappings/{id}` | Read one mapping |
| `PUT` | `/api/mappings/{id}` | Update |
| `DELETE` | `/api/mappings/{id}` | Delete |

`transform` ∈ `direct | upper | lower | concat | const`.

## Preview (dry-run)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/preview/{mapping_id}` | Transform `{"payload": [...]}` through the mapping **without persisting**. Returns the transformed rows. |

## Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/jobs` | List jobs |
| `POST` | `/api/jobs` | Create a job `{name, source_connector_id, target_connector_id, mapping_id, schedule_note?, status?}` |
| `GET` | `/api/jobs/{id}` | Read one job |
| `PUT` | `/api/jobs/{id}` | Update |
| `DELETE` | `/api/jobs/{id}` | Delete |
| `POST` | `/api/jobs/{id}/run` | Run the simulation, persist a run log → returns the run |

## Webhooks

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/webhooks` | List webhooks |
| `POST` | `/api/webhooks` | Register `{name, path, job_id}` |
| `DELETE` | `/api/webhooks/{id}` | Remove |
| `POST` | `/api/webhooks/hooks/{path}` | Fire webhook → runs the bound job → returns run log |

## Dashboard

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Aggregate job/run statistics + recent runs |

## Errors

All errors use FastAPI's standard shape:

```json
{"detail": "Connector not found"}
```

Validation errors return `422` with `detail: [{loc, msg, type}]`.
