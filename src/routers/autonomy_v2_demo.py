"""
Dev-only demo run endpoint for operator smoke tests.
Creates a synthetic run with demo events using RunStoreV2.
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
from typing import Any, Dict

from forge.autonomy.store.run_store_v2 import RunStoreV2
from forge.autonomy.events.event_bus_v2 import EventBusV2

router = APIRouter(prefix="/api/autonomy/v2", tags=["autonomy_v2_demo"])


def _utc_now() -> str:
    """ISO8601 UTC timestamp (SQLite-friendly)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _demo_graph() -> Dict[str, Any]:
    """Minimal demo graph payload."""
    return {
        "schema_version": "graph_v2",
        "nodes": [
            {"id": "start", "kind": "demo", "name": "Start"},
            {"id": "step_1", "kind": "demo", "name": "Collect"},
            {"id": "step_2", "kind": "demo", "name": "Decide"},
            {"id": "finish", "kind": "demo", "name": "Finish"},
        ],
        "edges": [
            {"from": "start", "to": "step_1"},
            {"from": "step_1", "to": "step_2"},
            {"from": "step_2", "to": "finish"},
        ],
    }


@router.post("/runs/demo")
def create_demo_run(request: Request):
    """
    Creates a demo run with synthetic events.

    DEV-ONLY: This endpoint is disabled in non-development environments.

    Returns:
        {"ok": true, "run_id": "<uuid>"}
    """
    # Safety guard: dev-only
    if os.getenv("FORGE_ENV", "development") != "development":
        raise HTTPException(status_code=404, detail="Not found")

    # Get session factory and event bus from app state
    get_db = request.app.state.get_db
    store = RunStoreV2(session_factory=get_db)
    event_bus = EventBusV2(session_factory=get_db)

    run_graph = _demo_graph()

    # Create run
    run_id = store.create_run_v2(
        env="local",
        lane="default",
        mode="demo",
        job_type="demo_smoke",
        requested_by="operator",
        run_graph=run_graph,
        params={"seed": True},
        parent_run_id=None,
    )

    # Emit events to EventBusV2 for UI consumption
    event_bus.publish(run_id, "run.created", {
        "message": "Demo run created",
        "job_type": "demo_smoke",
        "mode": "demo"
    })

    event_bus.publish(run_id, "run.started", {
        "message": "Run execution started"
    })

    event_bus.publish(run_id, "step.start", {
        "step_id": "start",
        "message": "Starting demo workflow"
    })

    event_bus.publish(run_id, "step.succeeded", {
        "step_id": "start",
        "message": "Start step completed"
    })

    event_bus.publish(run_id, "step.start", {
        "step_id": "step_1",
        "message": "Step 1: Collecting data"
    })

    event_bus.publish(run_id, "step.succeeded", {
        "step_id": "step_1",
        "message": "Data collection completed",
        "collected_items": 42
    })

    event_bus.publish(run_id, "step.start", {
        "step_id": "step_2",
        "message": "Step 2: Making decision"
    })

    event_bus.publish(run_id, "step.succeeded", {
        "step_id": "step_2",
        "message": "Decision made: proceed",
        "decision": "proceed"
    })

    event_bus.publish(run_id, "step.start", {
        "step_id": "finish",
        "message": "Finishing workflow"
    })

    event_bus.publish(run_id, "step.succeeded", {
        "step_id": "finish",
        "message": "Workflow finished successfully"
    })

    event_bus.publish(run_id, "run.succeeded", {
        "message": "Demo run completed successfully",
        "total_steps": 4,
        "duration_seconds": 0
    })

    # Load state and inject demo artifacts
    state = store.get_run_state_v2(run_id)

    # Ensure fields exist
    state.setdefault("step_states", {})
    state.setdefault("artifacts", {})

    # Add synthetic event stream to artifacts
    state["artifacts"]["demo_events"] = [
        {"ts": _utc_now(), "level": "info", "kind": "demo", "message": "Demo run created"},
        {"ts": _utc_now(), "level": "info", "kind": "demo", "message": "Step 1: Collect data"},
        {"ts": _utc_now(), "level": "info", "kind": "demo", "message": "Step 2: Make decision"},
        {"ts": _utc_now(), "level": "info", "kind": "demo", "message": "Finish successfully"},
    ]

    # Mark run as succeeded
    state["status"] = "succeeded"
    state["started_at"] = state.get("started_at") or _utc_now()
    state["finished_at"] = _utc_now()

    # Step states
    state["step_states"]["start"] = {"status": "succeeded", "updated_at": _utc_now()}
    state["step_states"]["step_1"] = {"status": "succeeded", "updated_at": _utc_now()}
    state["step_states"]["step_2"] = {"status": "succeeded", "updated_at": _utc_now()}
    state["step_states"]["finish"] = {"status": "succeeded", "updated_at": _utc_now()}

    # Persist updated state
    store.put_run_state_v2(run_id, state)

    return {"ok": True, "run_id": run_id}
