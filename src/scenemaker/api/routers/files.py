"""Serves signed download URLs when the local storage backend is in use."""

import mimetypes

from fastapi import APIRouter, HTTPException, Response, status

from scenemaker.api.deps import ServicesDep
from scenemaker.storage.local import LocalStorage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{key:path}")
def download(key: str, expires: int, token: str, services: ServicesDep) -> Response:
    storage = services.storage
    if not isinstance(storage, LocalStorage):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not served by this backend")
    if not storage.verify(key, expires, token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid or expired link")
    try:
        data = storage.get(key)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found") from exc
    media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)
