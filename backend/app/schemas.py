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
    is_public: bool
    published_at: datetime | None
    like_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicImageOut(BaseModel):
    """Metadata exposed on a public share link — no owner or internal ids."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    content_type: str
    created_at: datetime
    like_count: int = 0
    liked_by_me: bool = False


class ShareOut(BaseModel):
    share_token: str


class PublishOut(BaseModel):
    is_public: bool
    published_at: datetime | None
    share_token: str | None


class FeedItem(BaseModel):
    """One card in the public gallery. Keyed by share_token, never by row id."""

    share_token: str
    title: str
    description: str
    content_type: str
    published_at: datetime | None
    like_count: int
    liked_by_me: bool


class FeedPage(BaseModel):
    items: list[FeedItem]
    # Opaque cursor for the next page; null means the end of the feed.
    next_cursor: str | None


class LikeOut(BaseModel):
    like_count: int
    liked_by_me: bool
