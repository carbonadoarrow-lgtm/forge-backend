"""
Job command mappings for Forge OS.

This module defines the mapping between job names and their execution commands.
When a job is triggered, the system looks up the command here and executes it.
"""

from typing import Dict

# Job name → shell command mapping
JOB_COMMAND_SCRIPTS: Dict[str, str] = {
    # Health checks
    "forge_health_check_v1": "python -m scripts.run_health_check_with_jobs",

    # Leto BLRM
    "leto_blrm_v1": "python -m scripts.run_leto_blrm_with_jobs",
}


def get_job_command(job_name: str) -> str | None:
    """
    Get the shell command for a given job name.

    Args:
        job_name: Name of the job (e.g., "leto_blrm_v1")

    Returns:
        Shell command string, or None if job name not found
    """
    return JOB_COMMAND_SCRIPTS.get(job_name)


def list_available_jobs() -> list[str]:
    """
    List all available job names.

    Returns:
        List of job names
    """
    return list(JOB_COMMAND_SCRIPTS.keys())
