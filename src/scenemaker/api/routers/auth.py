from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from scenemaker.api.deps import CurrentUser, DbDep, ServicesDep
from scenemaker.db.models import Tenant, User
from scenemaker.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from scenemaker.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User, services: ServicesDep) -> TokenResponse:
    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        secret=services.settings.jwt_secret,
        expires_minutes=services.settings.jwt_expire_minutes,
    )
    return TokenResponse(access_token=token)


def _get_tenant(db: DbDep, slug: str) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True)))
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown tenant")
    return tenant


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbDep, services: ServicesDep) -> TokenResponse:
    tenant = _get_tenant(db, body.tenant_slug)
    email = body.email.lower()
    exists = db.scalar(select(User.id).where(User.tenant_id == tenant.id, User.email == email))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.commit()
    return _token_for(user, services)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep, services: ServicesDep) -> TokenResponse:
    tenant = _get_tenant(db, body.tenant_slug)
    user = db.scalar(
        select(User).where(User.tenant_id == tenant.id, User.email == body.email.lower())
    )
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return _token_for(user, services)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
