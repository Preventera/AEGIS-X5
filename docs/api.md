# REST API Reference

AEGIS-X5 exposes a REST API via FastAPI on port 4000 (Docker) or embedded.

Base URL: `http://localhost:4000/api/v1`

Swagger docs: `http://localhost:4000/api/docs`

---

## Authentication

All endpoints except `/api/v1/health` require an API key via the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-key-here" http://localhost:4000/api/v1/agents
```

Configure API keys via the `AEGIS_API_KEYS` environment variable (comma-separated):

```bash
AEGIS_API_KEYS=key1,key2,key3
```

If no keys are configured, all endpoints are open (development mode).

---

## Endpoints

### POST /api/v1/trace

Record a trace span.

**Request:**

```json
{
  "name": "llm-call",
  "workspace": "my-org",
  "start_time": 1712300000.0,
  "end_time": 1712300001.5,
  "attributes": {
    "model": "claude-sonnet",
    "tokens": 1250
  },
  "status": "ok"
}
```

**Response:**

```json
{
  "status": "ok",
  "span_id": "a1b2c3d4e5f6g7h8",
  "duration_ms": 1500.0
}
```

---

### POST /api/v1/guard/validate

Validate content through the guard pipeline.

**Request:**

```json
{
  "content": "The user's email is john@example.com and SSN is 123-45-6789",
  "context": {
    "ground_truth": ["John is a customer"]
  }
}
```

**Response:**

```json
{
  "passed": false,
  "needs_approval": false,
  "blocked_by": "pii-detector",
  "results": [
    {
      "rule": "pii-detector",
      "passed": false,
      "level": "N3",
      "message": "PII detected: email, ssn"
    },
    {
      "rule": "injection-detector",
      "passed": true,
      "level": "N4",
      "message": ""
    }
  ]
}
```

---

### GET /api/v1/health

Health check (no authentication required).

**Response:**

```json
{
  "status": "ok",
  "version": "0.3.0",
  "total_traces": 1542,
  "uptime": "running"
}
```

---

### GET /api/v1/agents

List all agents with their statistics.

**Response:**

```json
{
  "agents": [
    {
      "workspace": "production",
      "total_traces": 1200,
      "avg_latency_ms": 245.3,
      "guard_blocks": 3,
      "last_seen": 1712345678.0
    }
  ],
  "count": 1
}
```

---

### GET /api/v1/predictions

Active predictions and accuracy metrics.

**Response:**

```json
{
  "pending": [
    {
      "id": "pred-000001",
      "metric": "faithfulness",
      "agent_id": "agent-1",
      "predicted_value": 0.88,
      "horizon_hours": 48.0
    }
  ],
  "accuracy": {
    "count": 15,
    "mae": 0.023,
    "rmse": 0.031,
    "metrics": {
      "faithfulness": { "count": 10, "mae": 0.019, "rmse": 0.025 }
    }
  },
  "pending_count": 1
}
```

---

### GET /api/v1/stats

Aggregate trace statistics. Optional `?workspace=name` filter.

**Response:**

```json
{
  "total_traces": 1542,
  "avg_latency_ms": 234.5,
  "max_latency_ms": 2891.3,
  "guard_blocks": 7
}
```

---

### GET /api/v1/traces

Recent traces. Optional `?limit=50&workspace=name` parameters.

**Response:**

```json
{
  "traces": [
    {
      "name": "llm-call",
      "workspace": "production",
      "status": "ok",
      "duration_ms": 245.3,
      "created_at": 1712345678.0
    }
  ],
  "count": 50
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Invalid or missing API key |
| 404 | Endpoint not found |
| 422 | Validation error (malformed request body) |
| 500 | Internal server error |
