"""Tests for the job tracking module."""

from __future__ import annotations

import pytest

from video_explainer_mcp.jobs import (
    JobStatus,
    clear_jobs,
    create_job,
    get_job,
    update_job,
)


@pytest.fixture(autouse=True)
def _clean_jobs():
    """Clear jobs between tests."""
    clear_jobs()
    yield
    clear_jobs()


class TestJobLifecycle:
    """Tests for job creation, retrieval, and update."""

    def test_create_job(self):
        """Creates a job with a 12-char hex ID."""
        job = create_job("my-project")
        assert len(job.job_id) == 12
        assert job.project_id == "my-project"
        assert job.status == JobStatus.PENDING

    def test_get_job(self):
        """Retrieves job by ID."""
        job = create_job("test")
        found = get_job(job.job_id)
        assert found is not None
        assert found.job_id == job.job_id

    def test_get_missing_job(self):
        """Returns None for unknown job ID."""
        assert get_job("nonexistent") is None

    def test_update_status(self):
        """Updates job status and sets completed_at."""
        job = create_job("test")
        updated = update_job(job.job_id, status=JobStatus.COMPLETED)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None

    def test_update_with_output(self):
        """Updates output file and duration."""
        job = create_job("test")
        update_job(
            job.job_id,
            status=JobStatus.COMPLETED,
            output_file="/out/video.mp4",
            duration_seconds=42.5,
        )
        found = get_job(job.job_id)
        assert found is not None
        assert found.output_file == "/out/video.mp4"
        assert found.duration_seconds == 42.5

    def test_update_missing_job(self):
        """Returns None when updating unknown job."""
        assert update_job("nope", status=JobStatus.FAILED) is None

    def test_clear_jobs(self):
        """Clears all tracked jobs."""
        create_job("a")
        create_job("b")
        count = clear_jobs()
        assert count == 2
        assert get_job("a") is None

    def test_failed_job_has_error(self):
        """Failed jobs can store error messages."""
        job = create_job("test")
        update_job(job.job_id, status=JobStatus.FAILED, error="OOM")
        found = get_job(job.job_id)
        assert found is not None
        assert found.error == "OOM"
