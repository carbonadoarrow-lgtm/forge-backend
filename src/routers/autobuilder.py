"""
Autobuilder API router for running and managing autobuilder tasks.
"""

from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/autobuilder", tags=["autobuilder"])

# In-memory store for runs (replace with DB in production)
autobuilder_runs: dict = {}


class AutobuilderRunRequest(BaseModel):
    task_path: str
    lane: str = "default"
    mode: str = "dry-run"


class AutobuilderRun(BaseModel):
    run_id: str
    task_path: str
    lane: str
    mode: str
    status: str  # pending, running, succeeded, failed
    created_at: str
    updated_at: str
    duration_seconds: Optional[float] = None
    tests_ok: Optional[bool] = None
    policy_allowed: Optional[bool] = None
    summary: Optional[dict] = None
    logs: List[str] = []
    error_message: Optional[str] = None


@router.post("/run", response_model=AutobuilderRun)
def start_autobuilder_run(request: AutobuilderRunRequest):
    """Start a new autobuilder run."""
    run_id = f"ab_{uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat() + "Z"

    run = AutobuilderRun(
        run_id=run_id,
        task_path=request.task_path,
        lane=request.lane,
        mode=request.mode,
        status="pending",
        created_at=now,
        updated_at=now,
        logs=[f"[{now}] Autobuilder run {run_id} created"],
    )

    autobuilder_runs[run_id] = run.dict()

    # In real implementation, this would queue the task
    # For now, simulate immediate start
    autobuilder_runs[run_id]["status"] = "running"
    autobuilder_runs[run_id]["logs"].append(f"[{now}] Run started in {request.mode} mode")

    return AutobuilderRun(**autobuilder_runs[run_id])


@router.get("/runs", response_model=List[AutobuilderRun])
def list_autobuilder_runs(limit: int = 50):
    """List recent autobuilder runs."""
    runs = list(autobuilder_runs.values())
    runs.sort(key=lambda x: x["created_at"], reverse=True)
    return [AutobuilderRun(**r) for r in runs[:limit]]


@router.get("/run/{run_id}", response_model=AutobuilderRun)
def get_autobuilder_run(run_id: str):
    """Get details of a specific autobuilder run."""
    if run_id not in autobuilder_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return AutobuilderRun(**autobuilder_runs[run_id])


@router.get("/run/{run_id}/logs")
def get_autobuilder_logs(run_id: str):
    """Get logs for a specific autobuilder run."""
    if run_id not in autobuilder_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return {"run_id": run_id, "logs": autobuilder_runs[run_id].get("logs", [])}
