from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from scenemaker.api.deps import CurrentUser, DbDep, ServicesDep
from scenemaker.db.models import (
    JobKind,
    JobStatus,
    RenderJob,
    RenderJobSelfie,
    SceneTemplate,
    Selfie,
)
from scenemaker.schemas.jobs import JobCreate, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

AVATAR_SLOT = "avatar"


def _out(job: RenderJob, services: ServicesDep) -> dict:
    output_url = None
    if job.status == JobStatus.DONE and job.output_key:
        output_url = services.storage.download_url(
            job.output_key, services.settings.download_url_ttl_seconds
        )
    return {
        "id": job.id,
        "template_id": job.template_id,
        "kind": job.kind,
        "status": job.status,
        "attempts": job.attempts,
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "output_url": output_url,
    }


def _validate(body: JobCreate, template: SceneTemplate, selfies: dict[str, Selfie]) -> dict:
    """Check slots against the template and return the params stored on the job."""
    bad_request = status.HTTP_400_BAD_REQUEST
    slots = [s.slot for s in body.selfies]
    if len(set(slots)) != len(slots):
        raise HTTPException(bad_request, "each slot may be used once")
    missing = {s.selfie_id for s in body.selfies} - set(selfies)
    if missing:
        raise HTTPException(bad_request, f"unknown selfie ids: {sorted(missing)}")

    if body.kind == JobKind.FACE_SWAP:
        unknown = set(slots) - set(template.actor_slots)
        if unknown:
            raise HTTPException(bad_request, f"template has no actor slots {sorted(unknown)}")
        return {}

    if len(slots) != 1 or slots[0] != AVATAR_SLOT:
        raise HTTPException(
            bad_request, f"avatar jobs take exactly one selfie in slot '{AVATAR_SLOT}'"
        )
    preset = body.motion_preset or (template.motion_presets[0] if template.motion_presets else None)
    if preset is None or preset not in template.motion_presets:
        raise HTTPException(bad_request, f"choose a motion preset from {template.motion_presets}")
    return {"motion_preset": preset}


@router.post("", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def create_job(body: JobCreate, user: CurrentUser, db: DbDep, services: ServicesDep) -> dict:
    template = db.scalar(
        select(SceneTemplate).where(
            SceneTemplate.id == body.template_id,
            SceneTemplate.is_active.is_(True),
            or_(SceneTemplate.tenant_id.is_(None), SceneTemplate.tenant_id == user.tenant_id),
        )
    )
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "template not found")

    selfie_ids = [s.selfie_id for s in body.selfies]
    selfies = {
        s.id: s
        for s in db.scalars(
            select(Selfie).where(Selfie.user_id == user.id, Selfie.id.in_(selfie_ids))
        )
    }
    params = _validate(body, template, selfies)

    if user.credits < 1:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no render credits left")
    user.credits -= 1

    job = RenderJob(
        tenant_id=user.tenant_id,
        user_id=user.id,
        template_id=template.id,
        kind=body.kind,
        params=params,
        selfies=[RenderJobSelfie(selfie_id=s.selfie_id, slot=s.slot) for s in body.selfies],
    )
    db.add(job)
    db.commit()
    services.queue.push(job.id)
    return _out(job, services)


@router.get("", response_model=list[JobOut])
def list_jobs(user: CurrentUser, db: DbDep, services: ServicesDep) -> list[dict]:
    jobs = db.scalars(
        select(RenderJob).where(RenderJob.user_id == user.id).order_by(RenderJob.created_at.desc())
    ).all()
    return [_out(j, services) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: CurrentUser, db: DbDep, services: ServicesDep) -> dict:
    job = db.scalar(select(RenderJob).where(RenderJob.id == job_id, RenderJob.user_id == user.id))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return _out(job, services)
