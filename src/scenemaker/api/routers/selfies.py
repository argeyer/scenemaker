import uuid

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from scenemaker.api.deps import CurrentUser, DbDep, ServicesDep
from scenemaker.db.models import Selfie
from scenemaker.schemas.selfies import SelfieOut

router = APIRouter(prefix="/selfies", tags=["selfies"])

ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/heic": "heic"}


def _out(selfie: Selfie, services: ServicesDep) -> dict:
    return {
        "id": selfie.id,
        "content_type": selfie.content_type,
        "size_bytes": selfie.size_bytes,
        "created_at": selfie.created_at,
        "url": services.storage.download_url(
            selfie.storage_key, services.settings.download_url_ttl_seconds
        ),
    }


@router.post("", response_model=SelfieOut, status_code=status.HTTP_201_CREATED)
async def upload_selfie(
    file: UploadFile, user: CurrentUser, db: DbDep, services: ServicesDep
) -> dict:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "upload a JPEG, PNG, or HEIC")
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty file")
    if len(data) > services.settings.max_selfie_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "selfie too large")

    selfie_id = str(uuid.uuid4())
    extension = ALLOWED_TYPES[content_type]
    key = f"tenants/{user.tenant_id}/users/{user.id}/selfies/{selfie_id}.{extension}"
    services.storage.put(key, data, content_type)
    selfie = Selfie(
        id=selfie_id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        storage_key=key,
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(selfie)
    db.commit()
    return _out(selfie, services)


@router.get("", response_model=list[SelfieOut])
def list_selfies(user: CurrentUser, db: DbDep, services: ServicesDep) -> list[dict]:
    selfies = db.scalars(
        select(Selfie).where(Selfie.user_id == user.id).order_by(Selfie.created_at.desc())
    ).all()
    return [_out(s, services) for s in selfies]
