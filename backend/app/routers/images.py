import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Image, User
from ..schemas import ImageOut, ShareOut
from ..security import get_current_user
from ..storage import delete_file, path_for, save_upload

router = APIRouter(prefix="/images", tags=["images"])


def _owned_image(image_id: int, db: Session, user: User) -> Image:
    """Fetch an image, 404ing unless it belongs to the caller."""
    image = db.scalar(select(Image).where(Image.id == image_id, Image.owner_id == user.id))
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return image


@router.get("", response_model=list[ImageOut])
def list_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Image]:
    stmt = select(Image).where(Image.owner_id == current_user.id).order_by(Image.created_at.desc())
    return list(db.scalars(stmt))


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
) -> Image:
    return _owned_image(image_id, db, current_user)


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
) -> Image:
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
    return image


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
    db.commit()
