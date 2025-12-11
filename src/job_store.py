# server/job_store.py

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


JobStatus = Literal["pending", "running", "succeeded", "failed"]

# Path to jobs JSON file
JOBS_FILE = Path(__file__).parent.parent / "data" / "jobs.json"


@dataclass
class JobRecord:
    """
    Internal representation for a background job.

    This is intentionally decoupled from the Pydantic Job model in console_api
    to avoid circular imports. Fields mirror that model 1:1.
    """
    id: str
    name: str
    status: JobStatus
    created_at: str
    updated_at: str
    sphere: str  # "forge" | "orunmila"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sphere": self.sphere,
            "error_message": self.error_message,
        }


class JobStore:
    """
    Simple in-memory job store with a thread-safe API.

    This is meant as the single source of truth for "jobs" that appear in the
    Activity hub. Any long-running process (autobuilder, FLRM runs, etc.)
    should create + update a JobRecord via this store.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = Lock()
        self._load_from_disk()

    # -------- internal helpers --------

    def _now(self) -> str:
        # ISO-8601 string in UTC, matching other forge-os timestamps
        return datetime.utcnow().isoformat() + "Z"

    def _get(self, job_id: str) -> JobRecord:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise KeyError(f"Job with id '{job_id}' not found")

    def _load_from_disk(self) -> None:
        """
        Load jobs from JSON file on disk.

        If file is missing, starts with empty store.
        If file is corrupt, logs warning and starts with empty store.
        """
        if not JOBS_FILE.exists():
            logger.info(f"Jobs file not found at {JOBS_FILE}, starting with empty store")
            return

        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning(f"Jobs file {JOBS_FILE} does not contain a list, ignoring")
                return

            # Load each job record
            loaded_count = 0
            for job_dict in data:
                try:
                    # Create JobRecord from dict
                    rec = JobRecord(
                        id=job_dict["id"],
                        name=job_dict["name"],
                        status=job_dict["status"],
                        created_at=job_dict["created_at"],
                        updated_at=job_dict["updated_at"],
                        sphere=job_dict.get("sphere", "forge"),
                        error_message=job_dict.get("error_message"),
                    )
                    self._jobs[rec.id] = rec
                    loaded_count += 1
                except (KeyError, TypeError) as e:
                    logger.warning(f"Skipping malformed job record: {e}")
                    continue

            logger.info(f"Loaded {loaded_count} jobs from {JOBS_FILE}")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse jobs file {JOBS_FILE}: {e}, starting with empty store")
        except Exception as e:
            logger.warning(f"Unexpected error loading jobs from {JOBS_FILE}: {e}, starting with empty store")

    def _save_to_disk(self) -> None:
        """
        Save all jobs to JSON file atomically.

        Writes to temporary file first, then renames to avoid corruption.
        """
        # Ensure data directory exists
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Serialize all jobs
        jobs_list = [rec.to_dict() for rec in self._jobs.values()]

        # Write to temporary file
        tmp_file = JOBS_FILE.with_suffix(".json.tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(jobs_list, f, indent=2, ensure_ascii=False)

            # Atomic replace
            os.replace(tmp_file, JOBS_FILE)

            logger.debug(f"Persisted {len(jobs_list)} jobs to {JOBS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save jobs to disk: {e}")
            # Clean up tmp file if it exists
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except:
                    pass

    # -------- public API --------

    def list_jobs(self) -> List[JobRecord]:
        """
        Return all jobs, newest first.
        """
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )

    def get_job(self, job_id: str) -> JobRecord:
        with self._lock:
            return self._get(job_id)

    def create_job(
        self,
        job_id: str,
        name: str,
        status: JobStatus = "pending",
        sphere: str = "forge",
        error_message: Optional[str] = None,
    ) -> JobRecord:
        """
        Create a new job with a given id. Upstream callers are responsible for
        choosing a unique id (e.g., UUID, ULID, or "job-<timestamp>").
        """
        now = self._now()
        rec = JobRecord(
            id=job_id,
            name=name,
            status=status,
            created_at=now,
            updated_at=now,
            sphere=sphere,
            error_message=error_message,
        )
        with self._lock:
            self._jobs[job_id] = rec
            self._save_to_disk()

        logger.info(f"Created job {job_id} [{sphere}] with status '{status}'")
        return rec

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> JobRecord:
        """
        Update the status (and optional error) for a job.
        """
        with self._lock:
            rec = self._get(job_id)
            rec.status = status
            rec.updated_at = self._now()
            if error_message is not None:
                rec.error_message = error_message
            self._save_to_disk()

        logger.info(f"Updated job {job_id} to status '{status}' [sphere: {rec.sphere}]")
        return rec

    # Convenience wrappers

    def mark_pending(self, job_id: str) -> JobRecord:
        return self.update_status(job_id, "pending")

    def mark_running(self, job_id: str) -> JobRecord:
        return self.update_status(job_id, "running")

    def mark_succeeded(self, job_id: str) -> JobRecord:
        return self.update_status(job_id, "succeeded")

    def mark_failed(self, job_id: str, error_message: str) -> JobRecord:
        return self.update_status(job_id, "failed", error_message=error_message)


# Global singleton used across the app
job_store = JobStore()
