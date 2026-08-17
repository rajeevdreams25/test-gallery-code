import base64
import binascii
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Image, Like, User
from ..schemas import FeedItem, FeedPage, LikeOut, PublicImageOut
from ..security import get_current_user, get_current_user_optional
from ..storage import path_for

router = APIRouter(prefix="/public", tags=["public"])


def _naive_utc(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; normalise so comparisons line up."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _encode_cursor(published_at: datetime, image_id: int) -> str:
    raw = f"{_naive_utc(published_at).isoformat()}|{image_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        stamp, image_id = raw.rsplit("|", 1)
        return _naive_utc(datetime.fromisoformat(stamp)), int(image_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid cursor")


def _shared_image(token: str, db: Session) -> Image:
    # Only images with a live share_token are reachable here; revoking makes
    # this 404 whether or not the image is listed in the gallery.
    image = db.scalar(select(Image).where(Image.share_token == token))
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is invalid or has been revoked")
    return image


def _like_count(image_id: int, db: Session) -> int:
    return db.scalar(select(func.count(Like.id)).where(Like.image_id == image_id)) or 0


@router.get("/feed", response_model=FeedPage)
def public_feed(
    limit: int = Query(24, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
) -> FeedPage:
    """Newest published photos first, paginated by keyset for infinite scroll.

    Keyset rather than OFFSET: photos published while someone is scrolling
    shift every offset, which duplicates or skips rows. A cursor anchored to
    (published_at, id) keeps each page stable.
    """
    stmt = (
        select(Image, func.count(Like.id).label("like_count"))
        .outerjoin(Like, Like.image_id == Image.id)
        .where(Image.is_public.is_(True), Image.share_token.is_not(None))
        .group_by(Image.id)
        .order_by(Image.published_at.desc(), Image.id.desc())
        .limit(limit + 1)  # one extra row tells us whether more remain
    )

    if cursor:
        after, after_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Image.published_at < after,
                and_(Image.published_at == after, Image.id < after_id),
            )
        )

    rows = db.execute(stmt).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    liked_ids: set[int] = set()
    if viewer and rows:
        liked_ids = set(
            db.scalars(
                select(Like.image_id).where(
                    Like.user_id == viewer.id,
                    Like.image_id.in_([image.id for image, _ in rows]),
                )
            )
        )

    items = [
        FeedItem(
            share_token=image.share_token,
            title=image.title,
            description=image.description,
            content_type=image.content_type,
            published_at=image.published_at,
            like_count=count,
            liked_by_me=image.id in liked_ids,
        )
        for image, count in rows
    ]

    next_cursor = None
    if has_more and rows:
        last_image, _ = rows[-1]
        next_cursor = _encode_cursor(last_image.published_at, last_image.id)

    return FeedPage(items=items, next_cursor=next_cursor)


@router.get("/{token}", response_model=PublicImageOut)
def get_shared_image(
    token: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_current_user_optional),
) -> PublicImageOut:
    image = _shared_image(token, db)
    liked = False
    if viewer:
        liked = (
            db.scalar(
                select(Like.id).where(Like.image_id == image.id, Like.user_id == viewer.id)
            )
            is not None
        )
    return PublicImageOut(
        title=image.title,
        description=image.description,
        content_type=image.content_type,
        created_at=image.created_at,
        like_count=_like_count(image.id, db),
        liked_by_me=liked,
    )


@router.get("/{token}/file")
def get_shared_file(token: str, db: Session = Depends(get_db)) -> FileResponse:
    image = _shared_image(token, db)
    return FileResponse(path_for(image.stored_name), media_type=image.content_type)


@router.post("/{token}/like", response_model=LikeOut)
def like_image(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeOut:
    """Liking requires an account, so a count means something and can be undone."""
    image = _shared_image(token, db)

    db.add(Like(image_id=image.id, user_id=current_user.id))
    try:
        db.commit()
    except IntegrityError:
        # Already liked - the unique constraint makes this idempotent.
        db.rollback()

    return LikeOut(like_count=_like_count(image.id, db), liked_by_me=True)


@router.delete("/{token}/like", response_model=LikeOut)
def unlike_image(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LikeOut:
    image = _shared_image(token, db)

    like = db.scalar(
        select(Like).where(Like.image_id == image.id, Like.user_id == current_user.id)
    )
    if like is not None:
        db.delete(like)
        db.commit()

    return LikeOut(like_count=_like_count(image.id, db), liked_by_me=False)
