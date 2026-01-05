# D12B: Tick-Once Operator Action - Implementation Complete

## Summary

Successfully implemented a complete operational interface for Autonomy V2 runs, including:
- V2 API client with types, endpoints, and React hooks
- Runs list page with table view and demo run creation
- Run details page with operator actions (Tick Once, Cancel)
- Backend tick-once endpoint verification

## Implementation Details

### Frontend Components Created

#### 1. `lib/forge-v2/types.ts`
- TypeScript types for V2 API responses
- RunListItem, RunDetail, RunEventItem, RunEventsResponse
- CreateDemoRunRequest/Response, TickOnceResponse
- ArtifactItem interface

#### 2. `lib/forge-v2/endpoints.ts`
- API endpoint definitions using `NEXT_PUBLIC_FORGE_BACKEND_URL` (default: http://127.0.0.1:8000)
- Endpoints:
  - `listRuns(limit?, cursor?)` - GET /api/autonomy/v2/runs
  - `getRun(runId)` - GET /api/autonomy/v2/runs/{id}
  - `runEvents(runId, limit?, cursor?)` - GET /api/autonomy/v2/runs/{id}/events
  - `createDemoRun` - POST /api/autonomy/v2/runs
  - `tickOnce(runId)` - POST /api/autonomy/v2/runs/{id}/tick
  - `cancelRun(runId)` - POST /api/autonomy/v2/runs/{id}/cancel

#### 3. `lib/forge-v2/hooks.ts`
- React Query hooks for data fetching
- `useRunsV2({limit})` - Fetch runs list
- `useRunV2(runId)` - Fetch single run
- `useRunEventsV2(runId, {limit, refetchIntervalMs})` - Fetch events with polling
- `useCreateDemoRunV2()` - Create demo run mutation
- `useTickOnce()` - Tick once operator action
- `useCancelRun()` - Cancel run operator action
- `useAutoRefetchRunEvents()` - Auto-poll events when running

#### 4. `app/forge/runs/page.tsx`
- Functional table replacing placeholder
- Columns: Status, Job Type, Mode, Requested By, Env, Lane, Created At, Run ID
- "Create Demo Run" button (top-right)
- Row click navigates to run details
- Copy run ID functionality
- Loading and error states

#### 5. `app/forge/runs/[runId]/page.tsx`
- Two-column layout:
  - **Left:** Run Summary, Last Error (if failed), Artifacts list
  - **Right:** Events panel (reusing cockpit-v2 EventsPanel)
- Operator actions:
  - "Tick Once" button (disabled if terminal)
  - "Cancel" button (disabled if terminal)
- Auto-poll events every 2s when running
- Copy run ID functionality

### Components Updated

#### `components/shared/status-badge.tsx`
- Added support for V2 run statuses: `pending`, `scheduled`
- Maintains backward compatibility with existing statuses

### Backend Verification

The backend tick-once endpoint was already implemented in `src/routers/autonomy_v2_ops.py`:

**Endpoint:** `POST /api/autonomy/v2/runs/{run_id}/tick`

**Behavior:**
- Dev-only (checks `ENV` variable)
- Validates run exists
- Executes one deterministic tick via `GraphTickV2.tick_run(run_id)`
- Returns updated run status

**Router Registration:** Already registered in `forge/app.py`

## Usage

### 1. Start Backend
```bash
# From forge-backend directory
python -m forge.app
```

Ensure:
- `NEXT_PUBLIC_FORGE_BACKEND_URL` is set (default: http://127.0.0.1:8000)
- Backend is accessible from frontend

### 2. View Runs List
Navigate to: `/forge/runs`
- See all runs in a table
- Click "Create Demo Run" to create a new demo run
- Click any row to view run details

### 3. View Run Details
- Navigate to `/forge/runs/{runId}`
- View run summary, events, and artifacts
- Use "Tick Once" to manually advance the run (if running)
- Use "Cancel" to stop the run (if not terminal)
- Events auto-poll every 2 seconds when running

## Verification Commands

### PowerShell Verification

```powershell
# 1) Create a demo run
$demo = Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/autonomy/v2/runs" `
  -ContentType "application/json" `
  -Body '{"env":"local","lane":"default","mode":"dry_run","job_type":"autobuilder","requested_by":"operator"}'
$runId = $demo.run_id
Write-Host "Created run: $runId"

# 2) List runs
$runs = Invoke-RestMethod "http://127.0.0.1:8000/api/autonomy/v2/runs?limit=10"
$runs.runs | Format-Table -Property run_id, status, job_type, created_at

# 3) Get run details
$run = Invoke-RestMethod "http://127.0.0.1:8000/api/autonomy/v2/runs/$runId"
Write-Host "Run status: $($run.status)"

# 4) Tick once (operator action)
$tick = Invoke-RestMethod -Method POST "http://127.0.0.1:8000/api/autonomy/v2/runs/$runId/tick"
Write-Host "Tick result: $($tick.ok), Status: $($tick.status)"

# 5) Get events
$events = Invoke-RestMethod "http://127.0.0.1:8000/api/autonomy/v2/runs/$runId/events"
Write-Host "Events count: $($events.events.Count)"
```

### Bash Verification

```bash
# 1) Create a demo run
DEMO=$(curl -X POST "http://127.0.0.1:8000/api/autonomy/v2/runs" \
  -H "Content-Type: application/json" \
  -d '{"env":"local","lane":"default","mode":"dry_run","job_type":"autobuilder","requested_by":"operator"}')
RUN_ID=$(echo $DEMO | jq -r '.run_id')
echo "Created run: $RUN_ID"

# 2) List runs
curl "http://127.0.0.1:8000/api/autonomy/v2/runs?limit=10" | jq

# 3) Tick once
curl -X POST "http://127.0.0.1:8000/api/autonomy/v2/runs/$RUN_ID/tick" | jq

# 4) Get events
curl "http://127.0.0.1:8000/api/autonomy/v2/runs/$RUN_ID/events" | jq
```

## Architecture Decisions

### 1. Reused Components
- **EventsPanel:** Reused from `app/cockpit-v2/EventsPanel.tsx`
  - Already has filtering, pagination, JSON expansion
  - Works with V2 event structure
- **StatusBadge:** Extended to support V2 statuses
  - Maintains backward compatibility
  - Single source of truth for status display

### 2. API Client Structure
- Separate V2 client in `lib/forge-v2/`
- Does not interfere with existing V1 endpoints in `lib/api-config.ts`
- Clean separation of concerns

### 3. Polling Strategy
- Events poll every 2 seconds when status is "running"
- No polling when terminal (succeeded/failed/cancelled)
- Implemented via `useAutoRefetchRunEvents` helper

### 4. Operator Actions
- Tick Once and Cancel buttons only enabled for non-terminal runs
- Clear visual feedback (disabled states, loading spinners)
- Confirmation dialog for Cancel action

## Backend Notes

### Existing Implementation
The tick-once endpoint is already implemented in `src/routers/autonomy_v2_ops.py`:

```python
@router.post("/runs/{run_id}/tick")
def tick_once(run_id: str, request: Request):
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")
    
    ticker = getattr(request.app.state, "graph_tick_v2", None)
    if ticker is None:
        raise HTTPException(status_code=500, detail="graph_tick_v2 not initialized")
    
    ticker.tick_run(run_id)
    
    # Return latest state summary after tick
    get_db = request.app.state.get_db
    store = RunStoreV2(session_factory=get_db)
    state = store.get_run_state_v2(run_id)
    
    return {
        "ok": True,
        "run_id": run_id,
        "status": state.get("status"),
        "updated_at": _utc_now(),
    }
```

### Dev-Only Guard
The endpoint uses `_is_dev()` to check the environment:
```python
def _is_dev() -> bool:
    env = (os.getenv("ENV") or os.getenv("APP_ENV") or "dev").lower()
    return env in {"dev", "development", "local"}
```

### Security Considerations
- Currently dev-only (not production-safe)
- For production, consider:
  - Add admin token authentication
  - Add `AUTONOMY_V2_OPS_ENABLED` flag
  - Add audit logging for tick operations

## Future Enhancements

### Phase 2 (Operator Audit)
- Add operator action audit table
- Track who ticked which run and when
- Display audit history in run details

### Phase 3 (Production Safety)
- Add admin token requirement
- Add `AUTONOMY_V2_OPS_ENABLED` environment flag
- Add rate limiting on tick-once
- Add timeout protection

### Phase 4 (Enhanced UI)
- Add run timeline visualization
- Add step-by-step progress tracking
- Add real-time event streaming via WebSocket
- Add bulk actions (cancel multiple runs)

## Testing Checklist

- [x] V2 types defined correctly
- [x] Endpoints configured with correct URLs
- [x] React hooks work with React Query
- [x] Runs list page renders table
- [x] Create Demo Run button works
- [x] Run details page displays correctly
- [x] Tick Once operator action works
- [x] Cancel operator action works
- [x] Events auto-poll when running
- [x] Copy run ID functionality works
- [x] Loading and error states display correctly
- [x] Backend tick-once endpoint is accessible

## Conclusion

The implementation provides a complete operational interface for Autonomy V2 runs, enabling operators to:
- View and manage runs through a modern UI
- Manually advance runs with "Tick Once"
- Cancel runs when needed
- Monitor events in real-time with auto-polling
- Create demo runs for testing

The backend tick-once endpoint is already functional and properly integrated with the frontend.
