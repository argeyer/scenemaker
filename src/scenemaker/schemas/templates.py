from pydantic import BaseModel


class TemplateOut(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None
    duration_seconds: int
    actor_slots: list[str]
    motion_presets: list[str]
    preview_url: str | None


class TemplateDetailOut(TemplateOut):
    video_url: str
