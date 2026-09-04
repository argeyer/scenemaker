from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from scenemaker.api.deps import CurrentUser, DbDep, ServicesDep
from scenemaker.db.models import SceneTemplate
from scenemaker.schemas.templates import TemplateDetailOut, TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


def _visible(user: CurrentUser):
    return select(SceneTemplate).where(
        SceneTemplate.is_active.is_(True),
        or_(SceneTemplate.tenant_id.is_(None), SceneTemplate.tenant_id == user.tenant_id),
    )


def _out(template: SceneTemplate, services: ServicesDep, *, detail: bool) -> dict:
    ttl = services.settings.download_url_ttl_seconds
    data = {
        "id": template.id,
        "slug": template.slug,
        "title": template.title,
        "description": template.description,
        "duration_seconds": template.duration_seconds,
        "actor_slots": template.actor_slots,
        "motion_presets": template.motion_presets,
        "preview_url": (
            services.storage.download_url(template.preview_key, ttl)
            if template.preview_key
            else None
        ),
    }
    if detail:
        data["video_url"] = services.storage.download_url(template.video_key, ttl)
    return data


@router.get("", response_model=list[TemplateOut])
def list_templates(user: CurrentUser, db: DbDep, services: ServicesDep) -> list[dict]:
    templates = db.scalars(_visible(user).order_by(SceneTemplate.title)).all()
    return [_out(t, services, detail=False) for t in templates]


@router.get("/{template_id}", response_model=TemplateDetailOut)
def get_template(template_id: str, user: CurrentUser, db: DbDep, services: ServicesDep) -> dict:
    template = db.scalar(_visible(user).where(SceneTemplate.id == template_id))
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "template not found")
    return _out(template, services, detail=True)
