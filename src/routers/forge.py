from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from .. import schemas
from ..storage import load_list, save_list, load_single

router = APIRouter(prefix="/forge", tags=["forge"])


@router.get("/skills", response_model=List[schemas.Skill])
def get_skills() -> List[schemas.Skill]:
    """Get all Forge skills."""
    return load_list(schemas.Skill, "forge_skills.json")


@router.get("/skills/{skill_id}", response_model=schemas.Skill)
def get_skill(skill_id: str) -> schemas.Skill:
    """Get a specific Forge skill by ID."""
    skills = load_list(schemas.Skill, "forge_skills.json")
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/skills/{skill_id}/run", response_model=schemas.Run)
def run_skill(skill_id: str, body: schemas.RunRequest | None = None) -> schemas.Run:
    """Trigger a Forge skill run."""
    skills = load_list(schemas.Skill, "forge_skills.json")
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    runs = load_list(schemas.Run, "forge_runs.json")

    new_run = schemas.Run(
        id=f"forge-run-{int(datetime.utcnow().timestamp())}",
        type="skill",
        name=skill.name,
        sphere="forge",
        status="running",
        startTime=datetime.utcnow().isoformat() + "Z",
        triggerSource=(body.triggerSource if body else "manual"),
        skillId=skill_id,
    )
    runs.insert(0, new_run)
    save_list(runs, "forge_runs.json")
    return new_run


@router.get("/missions", response_model=List[schemas.Mission])
def get_missions() -> List[schemas.Mission]:
    """Get all Forge missions."""
    return load_list(schemas.Mission, "forge_missions.json")


@router.get("/missions/{mission_id}", response_model=schemas.Mission)
def get_mission(mission_id: str) -> schemas.Mission:
    """Get a specific Forge mission by ID."""
    missions = load_list(schemas.Mission, "forge_missions.json")
    mission = next((m for m in missions if m.id == mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("/missions/{mission_id}/run", response_model=schemas.Run)
def run_mission(mission_id: str, body: schemas.RunRequest | None = None) -> schemas.Run:
    """Trigger a Forge mission run."""
    missions = load_list(schemas.Mission, "forge_missions.json")
    mission = next((m for m in missions if m.id == mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    runs = load_list(schemas.Run, "forge_runs.json")

    new_run = schemas.Run(
        id=f"forge-run-{int(datetime.utcnow().timestamp())}",
        type="mission",
        name=mission.name,
        sphere="forge",
        status="running",
        startTime=datetime.utcnow().isoformat() + "Z",
        triggerSource=(body.triggerSource if body else "manual"),
        missionId=mission_id,
    )
    runs.insert(0, new_run)
    save_list(runs, "forge_runs.json")
    return new_run


@router.get("/runs", response_model=List[schemas.Run])
def get_runs() -> List[schemas.Run]:
    """Get all Forge runs."""
    return load_list(schemas.Run, "forge_runs.json")


@router.get("/runs/{run_id}", response_model=schemas.Run)
def get_run(run_id: str) -> schemas.Run:
    """Get a specific Forge run by ID."""
    runs = load_list(schemas.Run, "forge_runs.json")
    run = next((r for r in runs if r.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/logs", response_model=str)
def get_run_logs(run_id: str) -> str:
    """Get logs for a specific Forge run."""
    runs = load_list(schemas.Run, "forge_runs.json")
    run = next((r for r in runs if r.id == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Return sample logs for now
    return f"[{run.startTime}] Starting {run.type} run: {run.name}\n[{run.startTime}] Status: {run.status}\n"


@router.get("/reports", response_model=List[schemas.Report])
def get_reports() -> List[schemas.Report]:
    """Get all Forge reports."""
    return load_list(schemas.Report, "forge_reports.json")


@router.get("/reports/{report_id}", response_model=schemas.Report)
def get_report(report_id: str) -> schemas.Report:
    """Get a specific Forge report by ID."""
    reports = load_list(schemas.Report, "forge_reports.json")
    report = next((r for r in reports if r.id == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/artifacts", response_model=List[schemas.Artifact])
def get_artifacts() -> List[schemas.Artifact]:
    """Get all Forge artifacts."""
    return load_list(schemas.Artifact, "forge_artifacts.json")


@router.get("/artifacts/{artifact_id}", response_model=schemas.Artifact)
def get_artifact(artifact_id: str) -> schemas.Artifact:
    """Get a specific Forge artifact by ID."""
    artifacts = load_list(schemas.Artifact, "forge_artifacts.json")
    artifact = next((a for a in artifacts if a.id == artifact_id), None)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.get("/system/status", response_model=schemas.SystemStatus)
def get_system_status() -> schemas.SystemStatus:
    """Get Forge system status."""
    return load_single(schemas.SystemStatus, "forge_system_status.json")


# ---------- Mission Reports ----------

MISSION_REPORTS_FILE = "mission_reports.json"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@router.get(
    "/missions/{mission_id}/reports",
    response_model=List[schemas.MissionReport],
)
def get_mission_reports(mission_id: str) -> List[schemas.MissionReport]:
    """Get all reports for a specific mission."""
    reports = load_list(schemas.MissionReport, MISSION_REPORTS_FILE)
    return [r for r in reports if r.mission_id == mission_id]


@router.post(
    "/missions/{mission_id}/reports/generate",
    response_model=schemas.MissionReport,
)
def generate_mission_report(mission_id: str) -> schemas.MissionReport:
    """Generate a new mission report with aggregated statistics."""
    missions = load_list(schemas.Mission, "forge_missions.json")
    if not any(m.id == mission_id for m in missions):
        raise HTTPException(status_code=404, detail="Mission not found")

    runs = load_list(schemas.Run, "forge_runs.json")
    mission_runs = [r for r in runs if getattr(r, "missionId", None) == mission_id]

    total_runs = len(mission_runs)
    succeeded = len([r for r in mission_runs if r.status == "succeeded"])
    failed = len([r for r in mission_runs if r.status == "failed"])
    running = len([r for r in mission_runs if r.status == "running"])

    stats = {
        "total_runs": total_runs,
        "succeeded": succeeded,
        "failed": failed,
        "running": running,
    }

    status = "ok"
    if failed > 0:
        status = "warning"
    if failed > succeeded and failed > 0:
        status = "error"

    highlights = [
        f"Total runs: {total_runs}",
        f"Succeeded: {succeeded}",
        f"Failed: {failed}",
        f"Running: {running}",
    ]

    if failed > 0:
        highlights.append("Some runs failed; investigate errors in recent runs.")

    recommendations = []
    if failed > 0:
        recommendations.append(
            "Review the logs of the last failed run and check configuration changes."
        )
    if succeeded > 0:
        recommendations.append(
            "Consider scheduling this mission if it's not already automated."
        )

    now = _now_iso()
    report_id = f"mission-report-{int(datetime.utcnow().timestamp())}"

    # Simple markdown body
    lines = [
        f"# Mission Report for {mission_id}",
        "",
        f"Generated at: {now}",
        "",
        "## Summary",
        f"- Total runs: {total_runs}",
        f"- Succeeded: {succeeded}",
        f"- Failed: {failed}",
        f"- Running: {running}",
        "",
        "## Highlights",
    ]
    for h in highlights:
        lines.append(f"- {h}")
    lines.append("")
    if recommendations:
        lines.append("## Recommendations")
        for r in recommendations:
            lines.append(f"- {r}")
    raw_markdown = "\n".join(lines)

    reports = load_list(schemas.MissionReport, MISSION_REPORTS_FILE)
    report = schemas.MissionReport(
        id=report_id,
        mission_id=mission_id,
        sphere="forge",
        generated_at=now,
        status=status,
        stats=stats,
        highlights=highlights,
        recommendations=recommendations,
        raw_markdown=raw_markdown,
        generated_by="system",
    )
    reports.append(report)
    save_list(reports, MISSION_REPORTS_FILE)
    return report
