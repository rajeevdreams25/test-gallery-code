import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Image, Like, User
from ..schemas import ImageOut, PublishOut, ShareOut
from ..security import get_current_user
from ..storage import delete_file, path_for, save_upload

router = APIRouter(prefix="/images", tags=["images"])


def _owned_image(image_id: int, db: Session, user: User) -> Image:
    """Fetch an image, 404ing unless it belongs to the caller."""
    image = db.scalar(select(Image).where(Image.id == image_id, Image.owner_id == user.id))
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return image


def _with_likes(image: Image, db: Session) -> ImageOut:
    count = db.scalar(select(func.count(Like.id)).where(Like.image_id == image.id)) or 0
    return ImageOut.model_validate(image).model_copy(update={"like_count": count})


@router.get("", response_model=list[ImageOut])
def list_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImageOut]:
    # One grouped query rather than a count per image.
    stmt = (
        select(Image, func.count(Like.id).label("like_count"))
        .outerjoin(Like, Like.image_id == Image.id)
        .where(Image.owner_id == current_user.id)
        .group_by(Image.id)
        .order_by(Image.created_at.desc())
    )
    return [
        ImageOut.model_validate(image).model_copy(update={"like_count": count})
        for image, count in db.execute(stmt).all()
    ]


@router.post("", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Image:
    stored_name, size = save_upload(file)

    image = Image(
        owner_id=current_user.id,
        stored_name=stored_name,
        original_name=file.filename or stored_name,
        content_type=file.content_type,
        size=size,
        title=title or (file.filename or "Untitled"),
        description=description,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/{image_id}", response_model=ImageOut)
def get_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageOut:
    return _with_likes(_owned_image(image_id, db, current_user), db)


@router.get("/{image_id}/file")
def get_image_file(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    image = _owned_image(image_id, db, current_user)
    return FileResponse(path_for(image.stored_name), media_type=image.content_type)


@router.put("/{image_id}", response_model=ImageOut)
def update_image(
    image_id: int,
    title: str | None = Form(None),
    description: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageOut:
    image = _owned_image(image_id, db, current_user)

    if title is not None:
        image.title = title
    if description is not None:
        image.description = description

    if file is not None and file.filename:
        old_name = image.stored_name
        stored_name, size = save_upload(file)
        image.stored_name = stored_name
        image.original_name = file.filename
        image.content_type = file.content_type
        image.size = size
        delete_file(old_name)

    db.commit()
    db.refresh(image)
    return _with_likes(image, db)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    image = _owned_image(image_id, db, current_user)
    stored_name = image.stored_name

    db.delete(image)
    db.commit()
    delete_file(stored_name)


@router.post("/{image_id}/share", response_model=ShareOut)
def share_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareOut:
    """Create the public link, or return the existing one if already shared."""
    image = _owned_image(image_id, db, current_user)

    if not image.share_token:
        image.share_token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(image)

    return ShareOut(share_token=image.share_token)


@router.delete("/{image_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    image = _owned_image(image_id, db, current_user)
    image.share_token = None
    # The gallery serves photos through the share token, so pulling the link
    # necessarily removes the photo from the gallery too.
    image.is_public = False
    image.published_at = None
    db.commit()


@router.post("/{image_id}/publish", response_model=PublishOut)
def publish_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishOut:
    """List the photo in the public gallery.

    Publishing implies a shareable link, so this mints one if the photo does
    not already have it. Sharing alone never publishes - an unlisted link
    stays out of the gallery until the owner asks for this.
    """
    image = _owned_image(image_id, db, current_user)

    if not image.share_token:
        image.share_token = secrets.token_urlsafe(32)
    if not image.is_public:
        image.is_public = True
        image.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(image)
    return PublishOut(
        is_public=image.is_public,
        published_at=image.published_at,
        share_token=image.share_token,
    )


@router.delete("/{image_id}/publish", response_model=PublishOut)
def unpublish_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishOut:
    """Remove from the gallery but keep the unlisted link working."""
    image = _owned_image(image_id, db, current_user)

    image.is_public = False
    image.published_at = None
    db.commit()
    db.refresh(image)

    return PublishOut(
        is_public=image.is_public,
        published_at=image.published_at,
        share_token=image.share_token,
    )
