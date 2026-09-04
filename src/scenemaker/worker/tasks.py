"""Processing of a single render job. Shared by the worker loop and the tests."""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from scenemaker.ai.base import RenderRequest
from scenemaker.db.models import JobKind, JobStatus, RenderJob
from scenemaker.services import Services

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(db: Session, job_id: str) -> RenderJob | None:
    return db.get(RenderJob, job_id, options=[selectinload(RenderJob.selfies)])


def process_job(services: Services, job_id: str) -> None:
    """Run one job end to end and record the outcome on the job row.

    A job that fails is re-queued until it reaches the configured attempt
    limit, then marked FAILED with the last error.
    """
    with services.session_factory() as db:
        job = _load(db, job_id)
        if job is None:
            log.warning("job %s not found, dropping", job_id)
            return
        if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            log.info("job %s already %s, skipping", job_id, job.status.value)
            return

        job.status = JobStatus.RUNNING
        job.attempts += 1
        job.started_at = _now()
        db.commit()

        try:
            output_key = _render(services, db, job)
        except Exception as exc:  # noqa: BLE001 - any failure is recorded on the job
            log.exception("job %s attempt %d failed", job_id, job.attempts)
            job.error = f"{type(exc).__name__}: {exc}"[:2000]
            if job.attempts < services.settings.job_max_attempts:
                job.status = JobStatus.QUEUED
                db.commit()
                services.queue.push(job.id)
            else:
                job.status = JobStatus.FAILED
                job.finished_at = _now()
                db.commit()
            return

        job.output_key = output_key
        job.error = None
        job.status = JobStatus.DONE
        job.finished_at = _now()
        db.commit()
        log.info("job %s done", job_id)


def _render(services: Services, db: Session, job: RenderJob) -> str:
    storage = services.storage
    template = job.template
    request = RenderRequest(
        job_id=job.id,
        template_video=storage.get(template.video_key),
        selfies={link.slot: storage.get(link.selfie.storage_key) for link in job.selfies},
        params=dict(job.params),
    )
    if job.kind == JobKind.FACE_SWAP:
        video = services.generator.face_swap(request)
    else:
        video = services.generator.avatar_insert(request)

    output_key = f"tenants/{job.tenant_id}/users/{job.user_id}/renders/{job.id}.mp4"
    storage.put(output_key, video, "video/mp4")
    return output_key
