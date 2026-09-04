"""FastAPI dependencies: services, database session, and the authenticated user."""

from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from scenemaker.db.models import User
from scenemaker.security import decode_access_token
from scenemaker.services import Services

_bearer = HTTPBearer(auto_error=False)


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def get_db(services: ServicesDep) -> Iterator[Session]:
    session = services.session_factory()
    try:
        yield session
    finally:
        session.close()


DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    services: ServicesDep,
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing token")
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials, services.settings.jwt_secret)
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active or user.tenant_id != payload.get("tid"):
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
