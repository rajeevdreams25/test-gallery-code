from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    original_name: str
    content_type: str
    size: int
    share_token: str | None
    created_at: datetime
    updated_at: datetime


class PublicImageOut(BaseModel):
    """Metadata exposed on a public share link — no owner or internal ids."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    content_type: str
    created_at: datetime


class ShareOut(BaseModel):
    share_token: str
