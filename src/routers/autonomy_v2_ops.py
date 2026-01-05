from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from forge.autonomy.store.run_store_v2 import RunStoreV2


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_dev() -> bool:
    # Keep it simple + explicit. Adjust if you have a central settings object.
    env = (os.getenv("ENV") or os.getenv("APP_ENV") or "dev").lower()
    return env in {"dev", "development", "local"}


router = APIRouter(prefix="/api/autonomy/v2", tags=["autonomy_v2_ops"])


class CreateRunBody(BaseModel):
    env: str = "local"
    lane: str = "default"
    mode: str = "dry_run"
    job_type: str = "autobuilder"
    requested_by: str = "operator"
    run_graph: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    parent_run_id: Optional[str] = None


@router.post("/runs")
def create_run(body: CreateRunBody, request: Request):
    """
    Dev-only: create a run_v2 row + initial state blob.
    """
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")

    get_db = request.app.state.get_db
    store = RunStoreV2(session_factory=get_db)

    run_id = store.create_run_v2(
        env=body.env,
        lane=body.lane,
        mode=body.mode,
        job_type=body.job_type,
        requested_by=body.requested_by,
        run_graph=body.run_graph,
        params=body.params,
        parent_run_id=body.parent_run_id,
    )

    # If you already have an EventBusV2 emit API, you can emit run.created here.
    # Keeping minimal to avoid coupling.
    return {"ok": True, "run_id": run_id}


@router.post("/runs/{run_id}/tick")
def tick_once(run_id: str, request: Request):
    """
    Dev-only: deterministic operator tick for a single run.
    Calls GraphTickV2.tick_run(run_id) (your worker uses this).
    """
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")

    ticker = getattr(request.app.state, "graph_tick_v2", None)
    if ticker is None:
        raise HTTPException(status_code=500, detail="graph_tick_v2 not initialized")

    # WorkerV2.run_once() calls self.ticker.tick_run(run_id).
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


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request):
    """
    Dev-only: mark run cancelled.
    """
    if not _is_dev():
        raise HTTPException(status_code=404, detail="Not found")

    get_db = request.app.state.get_db
    store = RunStoreV2(session_factory=get_db)
    state = store.get_run_state_v2(run_id)

    if state.get("status") in {"succeeded", "failed", "cancelled"}:
        return {"ok": True, "run_id": run_id, "status": state.get("status")}

    state["status"] = "cancelled"
    state["finished_at"] = state.get("finished_at") or _utc_now()
    store.put_run_state_v2(run_id, state)

    # If you have EventBusV2 emit, emit run.cancelled here.
    return {"ok": True, "run_id": run_id, "status": "cancelled"}
