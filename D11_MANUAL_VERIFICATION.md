# D.11 Manual Verification Checklist

Quick manual spot checks to verify D.11 semantics against a running backend.

---

## Prerequisites

1. **Start the backend server:**
   ```bash
   cd "C:\Users\Jwmor\Desktop\Projects\vs code\forge-backend"
   uvicorn forge.app:create_app --factory --reload --port 8000
   ```

2. **Set admin token** (if not already set):
   ```bash
   export ADMIN_TOKEN="your_test_token_here"
   ```

---

## A) Auth Failure Shape

**Test:** Call admin endpoint WITHOUT `X-Admin-Token` header

**Command:**
```bash
curl -X POST http://localhost:8000/api/autonomy/v2/worker/tick_once \
  -H "Content-Type: application/json" \
  -d '{"env":"local","lane":"default","owner_id":"test","caps":{"max_total_ticks_per_invocation":1}}'
```

**Expected Response:**
- HTTP Status: `403`
- JSON Body:
  ```json
  {
    "detail": "Invalid or missing admin token"
  }
  ```

**Verify Audit Log:**
```bash
sqlite3 forge.db "SELECT action, result, actor_role, error_json FROM audit_log WHERE action='admin_auth' ORDER BY ts DESC LIMIT 1;"
```

Expected audit entry:
- `action`: `admin_auth`
- `result`: `denied`
- `actor_role`: `admin`
- `error_json`: `{"code": "INVALID_ADMIN_TOKEN", "message": "Invalid or missing admin token"}`

---

## B) Tick-Once Idle Response

**Test:** Call tick-once with NO runnable runs (and valid admin token)

**Command:**
```bash
curl -X POST http://localhost:8000/api/autonomy/v2/worker/tick_once \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your_test_token_here" \
  -d '{"env":"local","lane":"default","owner_id":"test","caps":{"max_total_ticks_per_invocation":10}}'
```

**Expected Response (when no runnable runs):**
- HTTP Status: `200`
- JSON Body:
  ```json
  {
    "status": "idle",
    "reason": "no_runnable_runs",
    "ticked_runs": 0,
    "events_added": 0,
    "message": "No runnable runs for local/default"
  }
  ```

**Verify Audit Log:**
```bash
sqlite3 forge.db "SELECT action, result, actor_id, payload_json FROM audit_log WHERE action='tick_once' AND result='idle' ORDER BY ts DESC LIMIT 1;"
```

Expected audit entry:
- `action`: `tick_once`
- `result`: `idle`
- `actor_id`: `test`
- `payload_json`: Contains `"env":"local"` and `"lane":"default"`

---

## C) /api/health Worker Guard Keys

**Test:** Verify worker guard information is always present

**Command:**
```bash
curl http://localhost:8000/api/health | python -m json.tool
```

**Expected Response:**

Must include `autonomy_v2_worker` object with these keys:
```json
{
  "autonomy_v2_worker": {
    "enabled": false,              // or true
    "reason": "...",               // e.g. "AUTONOMY_V2_WORKER_ENABLED=false"
    "pid": 12345,                  // current process ID
    "configured_pid": 0,           // from settings
    "tick_interval_seconds": 3,
    "env": "local",
    "lane": "default"
  },
  // ... other health data
}
```

**Verification:**
- `enabled` should be boolean
- `reason` should be non-empty string explaining why worker is enabled/disabled
- `pid` should be current process ID
- `configured_pid` should match `AUTONOMY_V2_WORKER_PID` setting
- `env` and `lane` should match `AUTONOMY_V2_WORKER_ENV` and `AUTONOMY_V2_WORKER_LANE`

---

## D) Audit Log Secret Sanitization

**Test:** Verify secrets are NOT logged in audit payloads

**Create audit entry with secrets:**
```python
# In a Python shell or script:
from forge.app import _audit

_audit(
    action="test_secrets",
    result="test",
    payload={
        "safe_field": "safe_value",
        "admin_token": "SECRET123",
        "password": "SECRET456",
        "api_key": "SECRET789"
    }
)
```

**Verify secrets are filtered:**
```bash
sqlite3 forge.db "SELECT payload_json FROM audit_log WHERE action='test_secrets' ORDER BY ts DESC LIMIT 1;"
```

**Expected:**
- `payload_json` should contain `"safe_field":"safe_value"`
- `payload_json` should NOT contain `admin_token`, `password`, or `api_key`

---

## E) Error Envelope Helper

**Test:** Verify `_error()` helper creates consistent structure

**Python shell test:**
```python
from forge.app import _error

# Basic error
err1 = _error("TEST_CODE", "Test message")
print(err1)
# Expected: {'error': {'code': 'TEST_CODE', 'message': 'Test message'}}

# Error with detail
err2 = _error("TEST_CODE", "Test message", detail={"extra": "info"})
print(err2)
# Expected: {'error': {'code': 'TEST_CODE', 'message': 'Test message', 'detail': {'extra': 'info'}}}
```

---

## Summary Checklist

- [ ] Auth failure returns HTTP 403 with proper error envelope
- [ ] Auth failure is audited with `INVALID_ADMIN_TOKEN` code
- [ ] Tick-once returns explicit idle response when no runnable runs
- [ ] Idle outcome is audited with result='idle'
- [ ] /api/health includes worker guard status with all required keys
- [ ] Audit log sanitizes secrets from payloads
- [ ] Error envelope helper creates consistent structure

---

## Notes

- All tests assume backend is running on `http://localhost:8000`
- Replace `your_test_token_here` with actual `ADMIN_TOKEN` value
- Some tests require specific backend state (e.g., no runnable runs for idle test)
- Audit log queries use SQLite CLI; adjust for your database setup
