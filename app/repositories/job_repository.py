"""Repositório de jobs (auditoria de execuções)."""
from __future__ import annotations

from app.models.job import Job, JobStatus
from app.models.base import utcnow
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    def start(self, kind: str) -> Job:
        return self.add(Job(kind=kind, status=JobStatus.RUNNING, started_at=utcnow()))

    def finish(self, job: Job, status: JobStatus, logs: str = "") -> Job:
        job.status = status
        job.finished_at = utcnow()
        job.logs = logs
        self.session.flush()
        return job
