"""Request and response schemas for authentication."""

from pydantic import BaseModel, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: SecretStr = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("username cannot be blank")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
