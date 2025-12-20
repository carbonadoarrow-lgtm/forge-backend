"""
Coding Lane API router for running and managing coding lane tasks.
"""

from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/coding-lane", tags=["coding-lane"])

# In-memory store for runs (replace with DB in production)
coding_lane_runs: dict = {}


class CodingLaneRunRequest(BaseModel):
    objective: str
    actor: str = "claude"
    lane: str = "default"
    mode: str = "dry-run"


class CodingLaneRun(BaseModel):
    run_id: str
    objective: str
    actor: str
    lane: str
    mode: str
    status: str  # pending, running, succeeded, failed
    created_at: str
    updated_at: str
    duration_seconds: Optional[float] = None
    tests_ok: Optional[bool] = None
    policy_allowed: Optional[bool] = None
    tool_calls: List[dict] = []
    trace: Optional[dict] = None
    summary: Optional[dict] = None
    logs: List[str] = []
    error_message: Optional[str] = None


@router.post("/run", response_model=CodingLaneRun)
def start_coding_lane_run(request: CodingLaneRunRequest):
    """Start a new coding lane run."""
    run_id = f"cl_{uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"

    run = CodingLaneRun(
        run_id=run_id,
        objective=request.objective,
        actor=request.actor,
        lane=request.lane,
        mode=request.mode,
        status="pending",
        created_at=now,
        updated_at=now,
        logs=[f"[{now}] Coding lane run {run_id} created"],
    )

    coding_lane_runs[run_id] = run.dict()

    # In real implementation, this would queue the task
    # For now, simulate immediate start
    coding_lane_runs[run_id]["status"] = "running"
    coding_lane_runs[run_id]["logs"].append(f"[{now}] Run started with actor: {request.actor}")

    return CodingLaneRun(**coding_lane_runs[run_id])


@router.get("/runs", response_model=List[CodingLaneRun])
def list_coding_lane_runs(limit: int = 50):
    """List recent coding lane runs."""
    runs = list(coding_lane_runs.values())
    runs.sort(key=lambda x: x["created_at"], reverse=True)
    return [CodingLaneRun(**r) for r in runs[:limit]]


@router.get("/run/{run_id}", response_model=CodingLaneRun)
def get_coding_lane_run(run_id: str):
    """Get details of a specific coding lane run."""
    if run_id not in coding_lane_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return CodingLaneRun(**coding_lane_runs[run_id])


@router.get("/run/{run_id}/logs")
def get_coding_lane_logs(run_id: str):
    """Get logs for a specific coding lane run."""
    if run_id not in coding_lane_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return {"run_id": run_id, "logs": coding_lane_runs[run_id].get("logs", [])}
