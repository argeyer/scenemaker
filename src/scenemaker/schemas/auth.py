from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    tenant_id: str
    email: str
    display_name: str | None
    credits: int
