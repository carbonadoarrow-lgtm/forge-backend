"""
Console API router for Activity hub and general console features.
"""

import os
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter

from .. import schemas
from ..job_store import job_store


router = APIRouter(prefix="/console", tags=["console"])


# Demo job seeding flag
DEMO_JOBS_SEEDED = False


def seed_demo_jobs_if_empty() -> None:
    """
    Seed a few demo jobs if the store is empty and demo mode is enabled.

    Set FORGE_CONSOLE_DEMO_JOBS=1 to enable demo job seeding.
    """
    global DEMO_JOBS_SEEDED
    if DEMO_JOBS_SEEDED:
        return

    # Only seed if explicitly requested
    if os.getenv("FORGE_CONSOLE_DEMO_JOBS", "0") != "1":
        return

    if job_store.list_jobs():
        DEMO_JOBS_SEEDED = True
        return

    job_store.create_job(
        job_id=str(uuid4()),
        name="Rebuild Orunmila workspace (demo)",
        status="succeeded",
    )
    job_store.create_job(
        job_id=str(uuid4()),
        name="Run FLRM v5 evaluation (demo)",
        status="running",
    )
    job_store.create_job(
        job_id=str(uuid4()),
        name="Sync Brainiac knowledge index (demo)",
        status="failed",
        error_message="Demo failure: connection timeout to S3 bucket.",
    )

    DEMO_JOBS_SEEDED = True


@router.get("/jobs", response_model=List[schemas.Job])
def list_jobs() -> List[schemas.Job]:
    """
    List all known jobs from the global JobStore.

    This is the single source of truth backing the Activity hub Jobs card
    and /forge/jobs page in forge-console.
    """
    seed_demo_jobs_if_empty()
    records = job_store.list_jobs()
    return [schemas.Job(**rec.to_dict()) for rec in records]


@router.post("/jobs/demo", response_model=schemas.Job)
def create_demo_job() -> schemas.Job:
    """
    Create a demo job for testing purposes.

    This endpoint simulates creating a job and running it through
    different states, useful for testing the Activity hub UI.
    """
    job_id = f"demo-{uuid4()}"
    job = job_store.create_job(
        job_id=job_id,
        name=f"Demo job {job_id[:8]}",
        status="pending",
    )
    return schemas.Job(**job.to_dict())


@router.post("/jobs", response_model=schemas.Job)
def create_job(job: schemas.Job) -> schemas.Job:
    """
    Create a new job.

    This endpoint allows background workers (autobuilder, FLRM runs, etc.)
    to register jobs that will appear in the Activity hub.
    """
    rec = job_store.create_job(
        job_id=job.id,
        name=job.name,
        status=job.status,
        sphere=job.sphere,
        error_message=job.error_message,
    )
    return schemas.Job(**rec.to_dict())


@router.get("/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: str) -> schemas.Job:
    """
    Get a specific job by ID.
    """
    rec = job_store.get_job(job_id)
    return schemas.Job(**rec.to_dict())


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    status: str,
    error_message: Optional[str] = None
) -> schemas.Job:
    """
    Update the status of a job.

    This endpoint is used by background workers to update job progress.
    """
    rec = job_store.update_status(job_id, status, error_message)
    return schemas.Job(**rec.to_dict())
