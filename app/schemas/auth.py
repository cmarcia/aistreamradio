from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator



class OAuthProviderInfo(BaseModel):
    id: str
    name: str
    icon_url: str | None = None


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() or not c.isalnum() for c in v):
            raise ValueError("Password must contain at least one letter and at least one digit or special character.")
        return v



class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str
    email: str
    exp: int
    iat: int
    iss: str = "aistreamradio-auth"


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
