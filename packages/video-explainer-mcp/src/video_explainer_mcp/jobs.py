"""In-memory render job tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JobStatus(str, Enum):
    """Render job lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RenderJob:
    """Tracks a background render operation."""

    job_id: str
    project_id: str
    status: JobStatus = JobStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    output_file: str = ""
    error: str = ""
    duration_seconds: float = 0.0


# Module-level job registry
_jobs: dict[str, RenderJob] = {}


def create_job(project_id: str) -> RenderJob:
    """Create and register a new render job.

    Args:
        project_id: The project being rendered.

    Returns:
        The newly created RenderJob.
    """
    job_id = uuid.uuid4().hex[:12]
    job = RenderJob(job_id=job_id, project_id=project_id)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> RenderJob | None:
    """Look up a render job by ID.

    Args:
        job_id: The 12-char hex job identifier.

    Returns:
        The RenderJob if found, None otherwise.
    """
    return _jobs.get(job_id)


def update_job(
    job_id: str,
    *,
    status: JobStatus | None = None,
    output_file: str | None = None,
    error: str | None = None,
    duration_seconds: float | None = None,
) -> RenderJob | None:
    """Update fields on an existing render job.

    Args:
        job_id: The job to update.
        status: New status.
        output_file: Path to rendered output.
        error: Error message on failure.
        duration_seconds: Elapsed render time.

    Returns:
        The updated RenderJob, or None if not found.
    """
    job = _jobs.get(job_id)
    if job is None:
        return None

    if status is not None:
        job.status = status
        if status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            job.completed_at = datetime.now(timezone.utc)
    if output_file is not None:
        job.output_file = output_file
    if error is not None:
        job.error = error
    if duration_seconds is not None:
        job.duration_seconds = duration_seconds
    return job


def clear_jobs() -> int:
    """Remove all tracked jobs. Returns count cleared."""
    count = len(_jobs)
    _jobs.clear()
    return count
