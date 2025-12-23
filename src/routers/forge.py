"""
Forge router - handles job-related operations.
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from ..schemas import JobCreate, JobUpdate, JobResponse, ErrorResponse
from ..storage import storage

router = APIRouter(prefix="/forge", tags=["forge"])


@router.get("/jobs", response_model=List[JobResponse])
async def get_all_jobs():
    """Get all jobs."""
    return storage.get_all_jobs()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a specific job by ID."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    return job


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job: JobCreate):
    """Create a new job."""
    return storage.create_job(job)


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, job_update: JobUpdate):
    """Update an existing job."""
    job = storage.update_job(job_id, job_update)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str):
    """Delete a job."""
    if not storage.delete_job(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )


@router.get("/jobs/search", response_model=List[JobResponse])
async def search_jobs(
    query: Optional[str] = Query(None, description="Search query for job title, description, company, or location"),
    skills: Optional[str] = Query(None, description="Comma-separated list of skills to filter by")
):
    """Search jobs by query and/or skills."""
    skills_list = None
    if skills:
        skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()]
    
    return storage.search_jobs(query=query, skills=skills_list)


@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "forge",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/skills", response_model=dict)
async def get_forge_skills():
    """Get all forge skills."""
    try:
        import json
        import os
        data_dir = os.getenv("DATA_DIR", "data")
        skills_file = os.path.join(data_dir, "forge_skills.json")
        if os.path.exists(skills_file):
            with open(skills_file, "r") as f:
                skills = json.load(f)
            return {"skills": skills, "count": len(skills)}
        else:
            return {"skills": [], "count": 0, "message": "Skills file not found"}
    except Exception as e:
        return {"skills": [], "count": 0, "error": str(e)}


@router.get("/missions", response_model=dict)
async def get_forge_missions():
    """Get all forge missions."""
    try:
        import json
        import os
        data_dir = os.getenv("DATA_DIR", "data")
        missions_file = os.path.join(data_dir, "forge_missions.json")
        if os.path.exists(missions_file):
            with open(missions_file, "r") as f:
                missions = json.load(f)
            return {"missions": missions, "count": len(missions)}
        else:
            return {"missions": [], "count": 0, "message": "Missions file not found"}
    except Exception as e:
        return {"missions": [], "count": 0, "error": str(e)}


@router.get("/info", response_model=dict)
async def get_forge_info():
    """Get forge system information."""
    try:
        import json
        import os
        data_dir = os.getenv("DATA_DIR", "data")
        status_file = os.path.join(data_dir, "forge_system_status.json")
        if os.path.exists(status_file):
            with open(status_file, "r") as f:
                status_data = json.load(f)
        else:
            status_data = {}
        
        return {
            "service": "forge",
            "version": "1.0.0",
            "status": "operational",
            "endpoints": ["/jobs", "/skills", "/missions", "/health"],
            "system_status": status_data
        }
    except Exception as e:
        return {
            "service": "forge",
            "version": "1.0.0",
            "status": "error",
            "error": str(e)
        }
