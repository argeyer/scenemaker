from datetime import datetime

from pydantic import BaseModel, Field

from scenemaker.db.models import JobKind, JobStatus


class SelfieSlot(BaseModel):
    selfie_id: str
    slot: str = Field(min_length=1, max_length=64)


class JobCreate(BaseModel):
    template_id: str
    kind: JobKind
    selfies: list[SelfieSlot] = Field(min_length=1)
    motion_preset: str | None = None


class JobOut(BaseModel):
    id: str
    template_id: str
    kind: JobKind
    status: JobStatus
    attempts: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    output_url: str | None
