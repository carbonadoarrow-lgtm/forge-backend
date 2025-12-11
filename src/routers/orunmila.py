from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from .. import schemas
from ..storage import load_list, save_list, load_single

router = APIRouter(prefix="/orunmila", tags=["orunmila"])


@router.get("/skills", response_model=List[schemas.Skill])
def get_skills() -> List[schemas.Skill]:
    """Get all Orunmila skills."""
    return load_list(schemas.Skill, "orunmila_skills.json")


@router.get("/skills/{skill_id}", response_model=schemas.Skill)
def get_skill(skill_id: str) -> schemas.Skill:
    """Get a specific Orunmila skill by ID."""
    skills = load_list(schemas.Skill, "orunmila_skills.json")
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/skills/{skill_id}/run", response_model=schemas.Run)
def run_skill(skill_id: str, body: schemas.RunRequest | None = None) -> schemas.Run:
    """Trigger an Orunmila skill run."""
    skills = load_list(schemas.Skill, "orunmila_skills.json")
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    runs = load_list(schemas.Run, "orunmila_runs.json")

    new_run = schemas.Run(
        id=f"xau-run-{int(datetime.utcnow().timestamp())}",
        type="skill",
        name=skill.name,
        sphere="orunmila",
        status="running",
        startTime=datetime.utcnow().isoformat() + "Z",
        triggerSource=(body.triggerSource if body else "manual"),
        skillId=skill_id,
    )
    runs.insert(0, new_run)
    save_list(runs, "orunmila_runs.json")
    return new_run


@router.get("/missions", response_model=List[schemas.Mission])
def get_missions() -> List[schemas.Mission]:
    """Get all Orunmila missions."""
    return load_list(schemas.Mission, "orunmila_missions.json")


@router.get("/missions/{mission_id}", response_model=schemas.Mission)
def get_mission(mission_id: str) -> schemas.Mission:
    """Get a specific Orunmila mission by ID."""
    missions = load_list(schemas.Mission, "orunmila_missions.json")
    mission = next((m for m in missions if m.id == mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("/missions/{mission_id}/run", response_model=schemas.Run)
def run_mission(mission_id: str, body: schemas.RunRequest | None = None) -> schemas.Run:
    """Trigger an Orunmila mission run."""
    missions = load_list(schemas.Mission, "orunmila_missions.json")
    mission = next((m for m in missions if m.id == mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    runs = load_list(schemas.Run, "orunmila_runs.json")

    new_run = schemas.Run(
        id=f"xau-run-{int(datetime.utcnow().timestamp())}",
        type="mission",
        name=mission.name,
        sphere="orunmila",
        status="running",
        startTime=datetime.utcnow().isoformat() + "Z",
        triggerSource=(body.triggerSource if body else "manual"),
        missionId=mission_id,
    )
    runs.insert(0, new_run)
    save_list(runs, "orunmila_runs.json")
    return new_run


@router.get("/runs", response_model=List[schemas.Run])
def get_runs() -> List[schemas.Run]:
    """Get all Orunmila runs."""
    return load_list(schemas.Run, "orunmila_runs.json")


@router.get("/runs/{run_id}", response_model=schemas.Run)
def get_run(run_id: str) -> schemas.Run:
    """Get a specific Orunmila run by ID."""
    runs = load_list(schemas.Run, "orunmila_runs.json")
    run = next((r for r in runs if r.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/logs", response_model=str)
def get_run_logs(run_id: str) -> str:
    """Get logs for a specific Orunmila run."""
    runs = load_list(schemas.Run, "orunmila_runs.json")
    run = next((r for r in runs if r.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Return sample logs for now
    return f"[{run.startTime}] Starting {run.type} run: {run.name}\n[{run.startTime}] Status: {run.status}\n"


@router.get("/reports", response_model=List[schemas.Report])
def get_reports() -> List[schemas.Report]:
    """Get all Orunmila reports."""
    return load_list(schemas.Report, "orunmila_reports.json")


@router.get("/reports/{report_id}", response_model=schemas.Report)
def get_report(report_id: str) -> schemas.Report:
    """Get a specific Orunmila report by ID."""
    reports = load_list(schemas.Report, "orunmila_reports.json")
    report = next((r for r in reports if r.id == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/state/daily", response_model=schemas.DailyState)
def get_daily_state() -> schemas.DailyState:
    """Get current daily state."""
    return load_single(schemas.DailyState, "orunmila_daily_state.json")


@router.get("/state/cycle-4w", response_model=schemas.Cycle4WState)
def get_cycle_state() -> schemas.Cycle4WState:
    """Get current 4-week cycle state."""
    return load_single(schemas.Cycle4WState, "orunmila_cycle4w_state.json")


@router.get("/state/structural", response_model=schemas.StructuralState)
def get_structural_state() -> schemas.StructuralState:
    """Get structural state."""
    return load_single(schemas.StructuralState, "orunmila_structural_state.json")


@router.get("/oracle/dashboard")
def get_oracle_dashboard():
    """Get Oracle dashboard data (consolidated view)."""
    return {
        "dailyState": load_single(schemas.DailyState, "orunmila_daily_state.json"),
        "cycleState": load_single(schemas.Cycle4WState, "orunmila_cycle4w_state.json"),
        "structuralState": load_single(schemas.StructuralState, "orunmila_structural_state.json"),
        "recentRuns": load_list(schemas.Run, "orunmila_runs.json")[:5],
        "recentReports": load_list(schemas.Report, "orunmila_reports.json")[:5],
    }
