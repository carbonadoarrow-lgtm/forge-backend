"""
Autonomy V2 API Router
Provides endpoints for the Cockpit V2 UI to interact with the autonomy system.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from pydantic import BaseModel
from datetime import datetime
import os

router = APIRouter(prefix="/api/autonomy/v2", tags=["autonomy-v2"])

# Admin token from environment
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def verify_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    request: Request = None
):
    """Verify admin token for protected endpoints. Accepts X-Admin-Token or x-admin-token."""
    if not ADMIN_TOKEN:
        # If no admin token configured, allow all requests (dev mode)
        return True

    # Try both header name variations for compatibility
    token = x_admin_token
    if not token and request:
        token = request.headers.get("X-Admin-Token") or request.headers.get("x-admin-token")

    if token != ADMIN_TOKEN:
        # D.11: Audit admin auth failure
        from forge.app import _audit
        _audit(
            action="admin_auth",
            result="denied",
            actor_role="admin",
            payload={"endpoint": request.url.path if request else "unknown"},
            error={"code": "INVALID_ADMIN_TOKEN", "message": "Invalid or missing admin token"}
        )
        raise HTTPException(status_code=403, detail="Invalid or missing admin token")
    return True

# Request/Response Models
class CreateRunRequest(BaseModel):
    env: str = "local"
    lane: str = "default"
    mode: str = "dry_run"
    job_type: str = "autobuilder"
    requested_by: str = "console"

class TickOnceRequest(BaseModel):
    env: str = "local"
    lane: str = "default"
    owner_id: str = "console"
    caps: Dict[str, int] = {
        "max_total_ticks_per_invocation": 10,
        "max_ticks_per_run_per_invocation": 10,
        "daily_tick_cap": 200
    }

class SetLaneEnabledRequest(BaseModel):
    env: str = "local"
    lane: str = "default"
    enabled: bool


@router.get("/runs")
async def list_runs(
    request: Request,
    env: str = "local",
    lane: str = "default"
) -> Dict[str, Any]:
    """
    List all runs for the given environment and lane.
    """
    try:
        run_store = request.app.state.run_store_v2

        # Get all runs from store
        with request.app.state.get_db() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT run_id, status, created_at, env, lane, mode, job_type, requested_by
                FROM runs_v2
                WHERE env = ? AND lane = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (env, lane)
            )
            rows = cur.fetchall()

            runs = []
            for row in rows:
                runs.append({
                    "run_id": row[0],
                    "status": row[1],
                    "created_at": row[2],
                    "env": row[3],
                    "lane": row[4],
                    "mode": row[5],
                    "job_type": row[6],
                    "requested_by": row[7]
                })

            return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> Dict[str, Any]:
    """
    Get detailed information about a specific run, including state and events.
    """
    try:
        run_store = request.app.state.run_store_v2
        event_bus = request.app.state.event_bus_v2

        # Get run info
        run = run_store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Get run state
        state = run_store.get_state(run_id)

        # Get run events
        with request.app.state.get_db() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT event_id, run_id, event_type, payload, created_at
                FROM events_v2
                WHERE run_id = ?
                ORDER BY created_at ASC
                """,
                (run_id,)
            )
            event_rows = cur.fetchall()

            events = []
            for row in event_rows:
                events.append({
                    "event_id": row[0],
                    "run_id": row[1],
                    "event_type": row[2],
                    "payload": row[3],
                    "created_at": row[4]
                })

        return {
            "run_id": run_id,
            "status": run.get("status"),
            "created_at": run.get("created_at"),
            "env": run.get("env"),
            "lane": run.get("lane"),
            "mode": run.get("mode"),
            "job_type": run.get("job_type"),
            "requested_by": run.get("requested_by"),
            "state": state,
            "events": events
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs")
async def create_run(
    payload: CreateRunRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Create a new run (noop or actual).
    """
    try:
        run_store = request.app.state.run_store_v2
        scheduler = request.app.state.scheduler_v2

        # Generate run_id
        import uuid
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        # Create run in store
        run_data = {
            "run_id": run_id,
            "env": payload.env,
            "lane": payload.lane,
            "mode": payload.mode,
            "job_type": payload.job_type,
            "requested_by": payload.requested_by,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        run_store.create_run(run_id, run_data)

        # Schedule the run
        scheduler.schedule_run(
            run_id=run_id,
            env=payload.env,
            lane=payload.lane,
            priority=100
        )

        return {
            "run_id": run_id,
            "status": "created",
            "message": "Run created and scheduled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/worker/status")
async def worker_status(
    request: Request,
    env: str = "local",
    lane: str = "default"
) -> Dict[str, Any]:
    """
    Get worker status for the given environment and lane.
    """
    try:
        kill_switch_registry = request.app.state.kill_switch_registry
        config_registry = request.app.state.config_registry

        # Check if lane is enabled
        lane_key = f"kill_switch.{env}.{lane}.lane_enabled"
        lane_config = config_registry.get(lane_key)
        lane_enabled = lane_config if lane_config is not None else True

        # Get worker stats
        with request.app.state.get_db() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT COUNT(*) FROM runs_v2
                WHERE env = ? AND lane = ? AND status = 'running'
                """,
                (env, lane)
            )
            active_runs = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*) FROM runs_v2
                WHERE env = ? AND lane = ? AND status = 'pending'
                """,
                (env, lane)
            )
            pending_runs = cur.fetchone()[0]

        return {
            "env": env,
            "lane": lane,
            "lane_enabled": lane_enabled,
            "active_runs": active_runs,
            "pending_runs": pending_runs,
            "status": "operational" if lane_enabled else "disabled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/worker/tick_once", dependencies=[Depends(verify_admin_token)])
async def tick_once(
    payload: TickOnceRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Manually trigger a single worker tick (admin only).

    D.11: Returns explicit idle outcome when no runnable runs found.
    """
    from forge.app import _audit

    try:
        worker = request.app.state.worker_v2
        SchedulerCaps = request.app.state.SchedulerCaps

        # Build caps object
        caps = SchedulerCaps(
            max_total_ticks_per_invocation=payload.caps.get("max_total_ticks_per_invocation", 10),
            max_ticks_per_run_per_invocation=payload.caps.get("max_ticks_per_run_per_invocation", 10),
            daily_tick_cap=payload.caps.get("daily_tick_cap", 200)
        )

        # Execute tick
        result = worker.tick_once(
            env=payload.env,
            lane=payload.lane,
            owner_id=payload.owner_id,
            caps=caps
        )

        ticked_runs = result.get("ticked_runs", 0)

        # D.11: Explicit idle outcome
        if ticked_runs == 0:
            # D.11: Audit idle outcome
            _audit(
                action="tick_once",
                result="idle",
                actor_id=payload.owner_id,
                actor_role="admin",
                payload={"env": payload.env, "lane": payload.lane},
            )
            return {
                "status": "idle",
                "reason": "no_runnable_runs",
                "ticked_runs": 0,
                "events_added": 0,
                "message": f"No runnable runs for {payload.env}/{payload.lane}"
            }

        # D.11: Audit successful tick
        _audit(
            action="tick_once",
            result="success",
            actor_id=payload.owner_id,
            actor_role="admin",
            payload={"env": payload.env, "lane": payload.lane, "ticked_runs": ticked_runs},
        )

        return {
            "status": "success",
            "ticked_runs": ticked_runs,
            "events_added": result.get("events_added", 0),
            "message": f"Tick completed for {payload.env}/{payload.lane}"
        }
    except Exception as e:
        # D.11: Audit failure
        _audit(
            action="tick_once",
            result="error",
            actor_id=payload.owner_id,
            actor_role="admin",
            payload={"env": payload.env, "lane": payload.lane},
            error={"code": "TICK_ERROR", "message": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill_switch/lane", dependencies=[Depends(verify_admin_token)])
async def set_lane_enabled(
    payload: SetLaneEnabledRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Enable or disable a worker lane (admin only).
    """
    try:
        config_registry = request.app.state.config_registry

        # Set lane enabled status
        lane_key = f"kill_switch.{payload.env}.{payload.lane}.lane_enabled"
        config_registry.set(lane_key, payload.enabled)

        return {
            "status": "success",
            "env": payload.env,
            "lane": payload.lane,
            "lane_enabled": payload.enabled,
            "message": f"Lane {payload.lane} {'enabled' if payload.enabled else 'disabled'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# D.12-A: Read-Only Operational Ergonomics Endpoints
# ============================================================================

def _parse_cursor(cursor_str: str, expected_parts: int = 2) -> List[str]:
    """Parse cursor string. Format: 'value1|value2|...'"""
    if not cursor_str:
        return []
    parts = cursor_str.split("|")
    if len(parts) != expected_parts:
        from forge.app import _error
        raise HTTPException(
            status_code=400,
            detail=_error("INVALID_CURSOR", "Cursor format invalid", {"expected_parts": expected_parts, "got": len(parts)})
        )
    return parts


def _encode_cursor(parts: List[str]) -> str:
    """Encode cursor from parts. Format: 'value1|value2|...'"""
    return "|".join(str(p) for p in parts)


@router.get("/runs")
async def list_runs(
    request: Request,
    env: Optional[str] = None,
    lane: Optional[str] = None,
    status: Optional[str] = None,
    requested_by: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    List runs with optional filtering and pagination.
    D.12-A read-only endpoint.

    Query params:
    - env: filter by environment
    - lane: filter by lane
    - status: filter by status
    - requested_by: filter by requester (substring match)
    - limit: max results (default 50, max 200)
    - cursor: pagination cursor (format: created_at|run_id)

    Returns:
    {
      "items": [{run_summary...}],
      "next_cursor": "..." | null
    }
    """
    from forge.app import _error

    try:
        # Validate limit
        if limit < 1 or limit > 200:
            raise HTTPException(
                status_code=400,
                detail=_error("INVALID_REQUEST", "limit must be between 1 and 200", {"limit": limit})
            )

        # Parse cursor if provided
        cursor_created_at = None
        cursor_run_id = None
        if cursor:
            try:
                parts = _parse_cursor(cursor, expected_parts=2)
                cursor_created_at = parts[0]
                cursor_run_id = parts[1]
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=_error("INVALID_CURSOR", "Failed to parse cursor", {"error": str(e)})
                )

        # Build query
        with request.app.state.get_db() as con:
            cur = con.cursor()

            # Build WHERE clauses
            where_clauses = []
            params = []

            if env:
                where_clauses.append("env = ?")
                params.append(env)

            if lane:
                where_clauses.append("lane = ?")
                params.append(lane)

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            if requested_by:
                where_clauses.append("requested_by LIKE ?")
                params.append(f"%{requested_by}%")

            # Cursor pagination (created_at DESC, run_id DESC)
            if cursor_created_at and cursor_run_id:
                where_clauses.append("(created_at < ? OR (created_at = ? AND run_id < ?))")
                params.extend([cursor_created_at, cursor_created_at, cursor_run_id])

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Fetch limit + 1 to determine if there's a next page
            query = f"""
                SELECT run_id, env, lane, mode, job_type, requested_by, status,
                       created_at, started_at, finished_at, last_error_json
                FROM runs_v2
                WHERE {where_sql}
                ORDER BY created_at DESC, run_id DESC
                LIMIT ?
            """
            params.append(limit + 1)

            cur.execute(query, params)
            rows = cur.fetchall()

        # Process results
        items = []
        has_more = len(rows) > limit
        result_rows = rows[:limit] if has_more else rows

        for row in result_rows:
            item = {
                "run_id": row[0],
                "env": row[1],
                "lane": row[2],
                "mode": row[3],
                "job_type": row[4],
                "requested_by": row[5],
                "status": row[6],
                "created_at": row[7],
                "started_at": row[8],
                "finished_at": row[9],
            }
            if row[10]:  # last_error_json
                import json
                try:
                    item["last_error"] = json.loads(row[10])
                except:
                    item["last_error"] = {"raw": row[10]}
            items.append(item)

        # Generate next cursor
        next_cursor = None
        if has_more and result_rows:
            last_row = result_rows[-1]
            next_cursor = _encode_cursor([last_row[7], last_row[0]])  # created_at, run_id

        return {
            "items": items,
            "next_cursor": next_cursor
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error("INTERNAL_ERROR", "Failed to list runs", {"error": str(e)})
        )


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: str) -> Dict[str, Any]:
    """
    Get run details by ID.
    D.12-A read-only endpoint.

    Returns run summary including:
    - Basic fields (env, lane, mode, job_type, requested_by, status)
    - Timestamps (created_at, started_at, finished_at)
    - last_error if present
    - tick counters if available (from run_state_v2)

    Returns 404 with RUN_NOT_FOUND if run doesn't exist.
    """
    from forge.app import _error

    try:
        with request.app.state.get_db() as con:
            cur = con.cursor()

            # Get run summary
            cur.execute(
                """
                SELECT run_id, env, lane, mode, job_type, requested_by, status,
                       created_at, started_at, finished_at, last_error_json, params_json,
                       run_graph_json
                FROM runs_v2
                WHERE run_id = ?
                """,
                (run_id,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=_error("RUN_NOT_FOUND", f"Run not found: {run_id}", {"run_id": run_id})
                )

            result = {
                "run_id": row[0],
                "env": row[1],
                "lane": row[2],
                "mode": row[3],
                "job_type": row[4],
                "requested_by": row[5],
                "status": row[6],
                "created_at": row[7],
                "started_at": row[8],
                "finished_at": row[9],
            }

            # Add optional fields
            if row[10]:  # last_error_json
                import json
                try:
                    result["last_error"] = json.loads(row[10])
                except:
                    result["last_error"] = {"raw": row[10]}

            if row[11]:  # params_json
                import json
                try:
                    result["params"] = json.loads(row[11])
                except:
                    pass

            if row[12]:  # run_graph_json
                import json
                try:
                    result["run_graph"] = json.loads(row[12])
                except:
                    pass

            # Try to get tick counters from run_state_v2
            cur.execute(
                "SELECT state_json FROM run_state_v2 WHERE run_id = ?",
                (run_id,)
            )
            state_row = cur.fetchone()
            if state_row and state_row[0]:
                import json
                try:
                    state = json.loads(state_row[0])
                    if "tick_count" in state:
                        result["tick_count"] = state["tick_count"]
                    if "ticks_used" in state:
                        result["ticks_used"] = state["ticks_used"]
                except:
                    pass

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error("INTERNAL_ERROR", "Failed to get run", {"error": str(e), "run_id": run_id})
        )


@router.get("/runs/{run_id}/events")
async def get_run_events(
    request: Request,
    run_id: str,
    limit: int = 200,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get events for a run with pagination.
    D.12-A read-only endpoint.

    Query params:
    - limit: max results (default 200, max 500)
    - cursor: pagination cursor (format: ts|id)

    Returns events in chronological order (ts ASC, id ASC).

    Returns:
    {
      "items": [{event...}],
      "next_cursor": "..." | null
    }

    Returns 404 with RUN_NOT_FOUND if run doesn't exist.
    """
    from forge.app import _error

    try:
        # Validate limit
        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=400,
                detail=_error("INVALID_REQUEST", "limit must be between 1 and 500", {"limit": limit})
            )

        # Parse cursor if provided
        cursor_ts = None
        cursor_id = None
        if cursor:
            try:
                parts = _parse_cursor(cursor, expected_parts=2)
                cursor_ts = parts[0]
                cursor_id = int(parts[1])
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=_error("INVALID_CURSOR", "Cursor ID must be numeric", {"error": str(e)})
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=_error("INVALID_CURSOR", "Failed to parse cursor", {"error": str(e)})
                )

        with request.app.state.get_db() as con:
            cur = con.cursor()

            # First check if run exists
            cur.execute("SELECT 1 FROM runs_v2 WHERE run_id = ?", (run_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail=_error("RUN_NOT_FOUND", f"Run not found: {run_id}", {"run_id": run_id})
                )

            # Build query for events
            where_clauses = ["run_id = ?"]
            params = [run_id]

            # Cursor pagination (ts ASC, id ASC)
            if cursor_ts and cursor_id is not None:
                where_clauses.append("(ts > ? OR (ts = ? AND id > ?))")
                params.extend([cursor_ts, cursor_ts, cursor_id])

            where_sql = " AND ".join(where_clauses)

            # Fetch limit + 1 to determine if there's a next page
            query = f"""
                SELECT id, run_id, ts, event_type, payload_json
                FROM run_events_v2
                WHERE {where_sql}
                ORDER BY ts ASC, id ASC
                LIMIT ?
            """
            params.append(limit + 1)

            cur.execute(query, params)
            rows = cur.fetchall()

        # Process results
        items = []
        has_more = len(rows) > limit
        result_rows = rows[:limit] if has_more else rows

        for row in result_rows:
            import json
            try:
                payload = json.loads(row[4])
            except:
                payload = {"raw": row[4]}

            items.append({
                "id": row[0],
                "run_id": row[1],
                "ts": row[2],
                "event_type": row[3],
                "payload": payload
            })

        # Generate next cursor
        next_cursor = None
        if has_more and result_rows:
            last_row = result_rows[-1]
            next_cursor = _encode_cursor([last_row[2], last_row[0]])  # ts, id

        return {
            "items": items,
            "next_cursor": next_cursor
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_error("INTERNAL_ERROR", "Failed to get run events", {"error": str(e), "run_id": run_id})
        )
