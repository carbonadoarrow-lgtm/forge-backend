#!/usr/bin/env python3
"""
Script to populate mock data for the Forge Backend.
This script creates sample job data for testing and development.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import JobCreate


def generate_mock_jobs(count: int = 10):
    """Generate mock job data."""
    
    job_titles = [
        "Senior Python Developer",
        "Machine Learning Engineer",
        "DevOps Engineer",
        "Frontend Developer",
        "Data Analyst",
        "Backend Engineer",
        "Full Stack Developer",
        "Cloud Architect",
        "Data Scientist",
        "Product Manager",
        "UX Designer",
        "QA Engineer",
        "Security Analyst",
        "Mobile Developer",
        "Database Administrator"
    ]
    
    companies = [
        "TechCorp Inc.",
        "AI Solutions Ltd.",
        "CloudSystems LLC",
        "WebTech Solutions",
        "DataInsights Corp.",
        "InnovateTech",
        "Digital Ventures",
        "Future Systems",
        "Smart Solutions",
        "Global Tech"
    ]
    
    locations = [
        "San Francisco, CA",
        "Remote",
        "New York, NY",
        "Austin, TX",
        "Chicago, IL",
        "Seattle, WA",
        "Boston, MA",
        "Los Angeles, CA",
        "Denver, CO",
        "Atlanta, GA"
    ]
    
    job_types = ["Full-time", "Part-time", "Contract", "Remote", "Hybrid"]
    experience_levels = ["Entry-Level", "Mid-Level", "Senior", "Lead"]
    
    skills_pool = [
        "Python", "FastAPI", "Docker", "AWS", "PostgreSQL", "REST APIs",
        "React", "TypeScript", "JavaScript", "CSS", "HTML", "Node.js",
        "TensorFlow", "PyTorch", "Scikit-learn", "NLP", "Machine Learning",
        "Kubernetes", "Terraform", "CI/CD", "Linux", "Git", "GitHub Actions",
        "SQL", "NoSQL", "MongoDB", "Redis", "Kafka", "RabbitMQ",
        "GraphQL", "WebSockets", "Microservices", "Serverless", "Lambda"
    ]
    
    jobs = []
    
    for i in range(count):
        # Generate random skills (3-6 skills per job)
        num_skills = random.randint(3, 6)
        skills = random.sample(skills_pool, num_skills)
        
        # Generate random dates (within last 30 days)
        days_ago = random.randint(0, 30)
        posted_date = datetime.now() - timedelta(days=days_ago)
        
        # Generate salary range based on experience level
        experience = random.choice(experience_levels)
        if experience == "Entry-Level":
            base_salary = random.randint(60000, 90000)
        elif experience == "Mid-Level":
            base_salary = random.randint(90000, 130000)
        else:  # Senior or Lead
            base_salary = random.randint(120000, 180000)
        
        salary_range = f"${base_salary:,} - ${base_salary + random.randint(20000, 40000):,}"
        
        job_data = {
            "id": f"job_{i+1:03d}",
            "title": random.choice(job_titles),
            "description": f"Exciting opportunity for a {experience.lower()} {random.choice(job_titles.split()[-1])} at {random.choice(companies)}. We're looking for someone passionate about technology and innovation.",
            "company": random.choice(companies),
            "location": random.choice(locations),
            "salary_range": salary_range,
            "job_type": random.choice(job_types),
            "experience_level": experience,
            "skills_required": skills,
            "posted_date": posted_date.isoformat() + "Z",
            "created_at": posted_date.isoformat() + "Z",
            "updated_at": posted_date.isoformat() + "Z"
        }
        
        jobs.append(job_data)
    
    return {"jobs": jobs}


def main():
    """Main function to populate mock data."""
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    output_file = data_dir / "mock_jobs.json"
    
    print(f"Generating mock job data...")
    mock_data = generate_mock_jobs(count=20)
    
    print(f"Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, indent=2, default=str)
    
    print(f"Successfully generated {len(mock_data['jobs'])} mock jobs.")
    print(f"File saved: {output_file}")
    
    # Also update the main jobs.json file if it exists
    main_jobs_file = data_dir / "jobs.json"
    if main_jobs_file.exists():
        print(f"\nUpdating main jobs.json file with mock data...")
        with open(main_jobs_file, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, indent=2, default=str)
        print(f"Updated {main_jobs_file}")
    
    print("\nSample job titles generated:")
    for i, job in enumerate(mock_data["jobs"][:5], 1):
        print(f"  {i}. {job['title']} at {job['company']} ({job['location']})")


if __name__ == "__main__":
    main()
