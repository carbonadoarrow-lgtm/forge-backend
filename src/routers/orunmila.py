"""
Orunmila router - handles LETO-BLRM integration and AI-related operations.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

router = APIRouter(prefix="/orunmila", tags=["orunmila"])


@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint for Orunmila service."""
    return {
        "status": "healthy",
        "service": "orunmila",
        "version": "1.0.0",
        "description": "LETO-BLRM Integration Service"
    }


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_job_description(job_description: Dict[str, Any]):
    """
    Analyze a job description using LETO-BLRM.
    
    Expected input:
    {
        "description": "Job description text",
        "title": "Job title",
        "company": "Company name"
    }
    """
    # Placeholder for LETO-BLRM integration
    # In a real implementation, this would call the LETO-BLRM API
    
    if not job_description.get("description"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is required"
        )
    
    description = job_description.get("description", "")
    
    # Mock analysis results
    return {
        "analysis_id": "mock_analysis_123",
        "status": "completed",
        "skills_identified": [
            "Python",
            "FastAPI",
            "Docker",
            "AWS",
            "REST APIs",
            "Data Analysis"
        ],
        "experience_level": "Mid-Level",
        "estimated_salary_range": "$80,000 - $120,000",
        "recommended_actions": [
            "Add more specific technical requirements",
            "Include remote work policy",
            "Specify team size and structure"
        ],
        "confidence_score": 0.85
    }


@router.post("/match", response_model=Dict[str, Any])
async def match_candidate_to_job(match_request: Dict[str, Any]):
    """
    Match a candidate profile to job requirements using LETO-BLRM.
    
    Expected input:
    {
        "candidate_skills": ["Python", "FastAPI", "Docker"],
        "job_requirements": {
            "required_skills": ["Python", "AWS"],
            "preferred_skills": ["Docker", "Kubernetes"]
        }
    }
    """
    candidate_skills = match_request.get("candidate_skills", [])
    job_requirements = match_request.get("job_requirements", {})
    
    if not candidate_skills or not job_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate skills and job requirements are required"
        )
    
    required_skills = job_requirements.get("required_skills", [])
    preferred_skills = job_requirements.get("preferred_skills", [])
    
    # Calculate match score
    matched_required = [skill for skill in required_skills if skill in candidate_skills]
    matched_preferred = [skill for skill in preferred_skills if skill in candidate_skills]
    
    required_match_percentage = len(matched_required) / len(required_skills) if required_skills else 1.0
    preferred_match_percentage = len(matched_preferred) / len(preferred_skills) if preferred_skills else 1.0
    
    total_match_score = (required_match_percentage * 0.7 + preferred_match_percentage * 0.3) * 100
    
    return {
        "match_id": "mock_match_456",
        "candidate_skills": candidate_skills,
        "matched_required_skills": matched_required,
        "matched_preferred_skills": matched_preferred,
        "missing_required_skills": [skill for skill in required_skills if skill not in candidate_skills],
        "missing_preferred_skills": [skill for skill in preferred_skills if skill not in candidate_skills],
        "match_score": round(total_match_score, 2),
        "recommendation": "Good match" if total_match_score >= 70 else "Needs improvement",
        "suggested_skills_to_learn": [
            skill for skill in required_skills + preferred_skills 
            if skill not in candidate_skills
        ][:3]  # Top 3 skills to learn
    }


@router.get("/status", response_model=Dict[str, Any])
async def get_service_status():
    """Get the current status of the Orunmila service."""
    return {
        "service": "orunmila",
        "status": "operational",
        "version": "1.0.0",
        "uptime": "99.9%",
        "last_updated": "2024-01-01T00:00:00Z",
        "features": [
            "Job description analysis",
            "Candidate-job matching",
            "Skill extraction",
            "Salary estimation"
        ]
    }


def _validate_safe_path(data_dir: str, filename: str) -> str:
    """
    Validate that the resulting path is within the allowed data directory.
    Prevents path traversal attacks.
    """
    import os
    # Get absolute path of data directory
    abs_data_dir = os.path.abspath(data_dir)
    # Construct the full path
    file_path = os.path.join(abs_data_dir, filename)
    # Get absolute path and resolve any ../ or symlinks
    abs_file_path = os.path.abspath(os.path.realpath(file_path))
    # Ensure the file is within the data directory
    if not abs_file_path.startswith(abs_data_dir + os.sep):
        raise ValueError(f"Path traversal detected: {filename}")
    return abs_file_path


@router.get("/state/daily", response_model=dict)
async def get_daily_state():
    """Get daily state for Orunmila."""
    try:
        import json
        import os
        data_dir = os.getenv("DATA_DIR", "data")
        state_file = _validate_safe_path(data_dir, "orunmila_daily_state.json")
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                state_data = json.load(f)
            return {
                "service": "orunmila",
                "state_type": "daily",
                "data": state_data,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        else:
            return {
                "service": "orunmila",
                "state_type": "daily",
                "data": {},
                "message": "Daily state file not found",
                "timestamp": "2024-01-01T00:00:00Z"
            }
    except Exception as e:
        return {
            "service": "orunmila",
            "state_type": "daily",
            "data": {},
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }
