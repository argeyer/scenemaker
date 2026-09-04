"""Hugging Face Inference Endpoint adapter.

Each job kind targets its own endpoint URL. The request is a multipart POST with
the template video, one selfie file per slot, and a JSON params field. The
endpoint must respond with the rendered video bytes (video/mp4). Adjust
`_build_files` if the deployed model expects a different contract.
"""

import base64
import json

import httpx

from scenemaker.ai.base import RenderRequest


class HuggingFaceVideoGenerator:
    def __init__(
        self,
        *,
        api_token: str,
        face_swap_endpoint: str,
        avatar_endpoint: str,
        timeout_seconds: float = 600.0,
    ) -> None:
        self.face_swap_endpoint = face_swap_endpoint
        self.avatar_endpoint = avatar_endpoint
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_token}"}, timeout=timeout_seconds
        )

    @staticmethod
    def _build_files(request: RenderRequest) -> list[tuple[str, tuple[str, bytes, str]]]:
        files = [("template", ("template.mp4", request.template_video, "video/mp4"))]
        for slot, data in request.selfies.items():
            files.append((f"selfie[{slot}]", (f"{slot}.jpg", data, "image/jpeg")))
        return files

    def _call(self, endpoint: str, request: RenderRequest) -> bytes:
        if not endpoint:
            raise RuntimeError("Hugging Face endpoint URL is not configured")
        response = self.client.post(
            endpoint,
            files=self._build_files(request),
            data={"params": json.dumps({"job_id": request.job_id, **request.params})},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("video/"):
            return response.content
        # Some endpoints return JSON with the video base64-encoded.
        payload = response.json()
        if "video_base64" in payload:
            return base64.b64decode(payload["video_base64"])
        if "video_url" in payload:
            video = self.client.get(payload["video_url"])
            video.raise_for_status()
            return video.content
        raise RuntimeError(f"unexpected response from AI endpoint: {content_type or 'unknown'}")

    def face_swap(self, request: RenderRequest) -> bytes:
        return self._call(self.face_swap_endpoint, request)

    def avatar_insert(self, request: RenderRequest) -> bytes:
        return self._call(self.avatar_endpoint, request)
