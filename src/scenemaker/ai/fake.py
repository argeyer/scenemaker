"""Deterministic stand-in used by tests and local development without a GPU."""

from scenemaker.ai.base import RenderRequest


class FakeVideoGenerator:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, RenderRequest]] = []

    def _render(self, kind: str, request: RenderRequest) -> bytes:
        self.calls.append((kind, request))
        if self.fail:
            raise RuntimeError("fake generator configured to fail")
        slots = ",".join(sorted(request.selfies))
        header = f"FAKE-VIDEO kind={kind} job={request.job_id} slots={slots}\n".encode()
        return header + request.template_video

    def face_swap(self, request: RenderRequest) -> bytes:
        return self._render("face_swap", request)

    def avatar_insert(self, request: RenderRequest) -> bytes:
        return self._render("avatar", request)
