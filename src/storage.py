"""
Data storage layer for the Forge Backend.
Supports file-based storage for development and testing.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import settings
from .schemas import JobCreate, JobUpdate, JobResponse


class FileStorage:
    """File-based storage for jobs data."""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.jobs_file = self.data_dir / "jobs.json"
        self._ensure_data_dir()
        self._load_data()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self):
        """Load data from JSON file."""
        if self.jobs_file.exists():
            with open(self.jobs_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {"jobs": []}
            self._save_data()
    
    def _save_data(self):
        """Save data to JSON file."""
        with open(self.jobs_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def get_all_jobs(self) -> List[JobResponse]:
        """Get all jobs."""
        jobs = []
        for job_data in self.data.get("jobs", []):
            job_data["id"] = str(job_data.get("id", ""))
            jobs.append(JobResponse(**job_data))
        return jobs
    
    def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Get a job by ID."""
        for job_data in self.data.get("jobs", []):
            if str(job_data.get("id", "")) == job_id:
                job_data["id"] = str(job_data.get("id", ""))
                return JobResponse(**job_data)
        return None
    
    def create_job(self, job: JobCreate) -> JobResponse:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        now = datetime.now()
        
        job_data = job.model_dump()
        job_data["id"] = job_id
        job_data["created_at"] = now
        job_data["updated_at"] = now
        
        self.data["jobs"].append(job_data)
        self._save_data()
        
        return JobResponse(**job_data)
    
    def update_job(self, job_id: str, job_update: JobUpdate) -> Optional[JobResponse]:
        """Update an existing job."""
        for i, job_data in enumerate(self.data.get("jobs", [])):
            if str(job_data.get("id", "")) == job_id:
                # Update only provided fields
                update_data = job_update.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    job_data[key] = value
                
                job_data["updated_at"] = datetime.now()
                self.data["jobs"][i] = job_data
                self._save_data()
                
                job_data["id"] = str(job_data.get("id", ""))
                return JobResponse(**job_data)
        return None
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        for i, job_data in enumerate(self.data.get("jobs", [])):
            if str(job_data.get("id", "")) == job_id:
                self.data["jobs"].pop(i)
                self._save_data()
                return True
        return False
    
    def search_jobs(self, query: str = None, skills: List[str] = None) -> List[JobResponse]:
        """Search jobs by query and/or skills."""
        results = []
        for job_data in self.data.get("jobs", []):
            job_data["id"] = str(job_data.get("id", ""))
            job = JobResponse(**job_data)
            
            match = True
            
            if query:
                query_lower = query.lower()
                title_match = query_lower in job.title.lower()
                desc_match = query_lower in job.description.lower()
                company_match = query_lower in job.company.lower()
                location_match = query_lower in job.location.lower()
                
                if not (title_match or desc_match or company_match or location_match):
                    match = False
            
            if skills and match:
                job_skills_lower = [s.lower() for s in job.skills_required]
                skills_lower = [s.lower() for s in skills]
                
                # Check if any required skill matches
                if not any(skill in job_skills_lower for skill in skills_lower):
                    match = False
            
            if match:
                results.append(job)
        
        return results


# Create global storage instance
storage = FileStorage()
