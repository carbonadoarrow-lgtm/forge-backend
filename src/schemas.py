"""
Pydantic schemas for data validation in the Forge Backend.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JobBase(BaseModel):
    """Base schema for job data."""
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Job description")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    salary_range: Optional[str] = Field(None, description="Salary range")
    job_type: str = Field(..., description="Full-time, Part-time, Contract, etc.")
    experience_level: str = Field(..., description="Entry, Mid, Senior, etc.")
    skills_required: List[str] = Field(default_factory=list, description="Required skills")
    posted_date: datetime = Field(default_factory=datetime.now, description="When job was posted")


class JobCreate(JobBase):
    """Schema for creating a new job."""
    pass


class JobUpdate(BaseModel):
    """Schema for updating a job."""
    title: Optional[str] = None
    description: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    skills_required: Optional[List[str]] = None


class JobResponse(JobBase):
    """Schema for job response."""
    id: str = Field(..., description="Unique job ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
