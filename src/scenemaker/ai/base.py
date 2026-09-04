"""Interface for the external AI service that produces the final video."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RenderRequest:
    job_id: str
    template_video: bytes
    selfies: dict[str, bytes] = field(default_factory=dict)
    """Selfie bytes keyed by actor slot (face swap) or a single "avatar" key."""
    params: dict = field(default_factory=dict)


class VideoGenerator(Protocol):
    def face_swap(self, request: RenderRequest) -> bytes:
        """Replace actor faces in the template with the users' faces. Returns video bytes."""
        ...

    def avatar_insert(self, request: RenderRequest) -> bytes:
        """Build an avatar from a selfie and insert it with a motion preset. Returns video bytes."""
        ...
