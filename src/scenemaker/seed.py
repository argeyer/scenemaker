"""Demo data for local development and tests."""

from sqlalchemy import select

from scenemaker.db.base import Base
from scenemaker.db.models import SceneTemplate, Tenant
from scenemaker.services import Services

DEMO_TENANT_SLUG = "demo"
DEMO_TEMPLATE_SLUG = "heist-lobby"


def seed_dev_data(services: Services) -> tuple[Tenant, SceneTemplate]:
    """Create the demo tenant and a shared template. Safe to run repeatedly."""
    Base.metadata.create_all(services.engine)
    with services.session_factory() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
        if tenant is None:
            tenant = Tenant(slug=DEMO_TENANT_SLUG, name="Demo Tenant", plan="pro")
            db.add(tenant)

        template = db.scalar(
            select(SceneTemplate).where(
                SceneTemplate.tenant_id.is_(None), SceneTemplate.slug == DEMO_TEMPLATE_SLUG
            )
        )
        if template is None:
            video_key = f"templates/{DEMO_TEMPLATE_SLUG}/scene.mp4"
            if not services.storage.exists(video_key):
                services.storage.put(video_key, b"PLACEHOLDER-TEMPLATE-VIDEO", "video/mp4")
            template = SceneTemplate(
                slug=DEMO_TEMPLATE_SLUG,
                title="The Lobby Heist",
                description="Two leads walk through a lobby. Swap either face or add an avatar.",
                video_key=video_key,
                duration_seconds=12,
                actor_slots=["lead", "partner"],
                motion_presets=["walk_in", "turn_and_smile"],
            )
            db.add(template)
        db.commit()
        db.refresh(tenant)
        db.refresh(template)
        return tenant, template
