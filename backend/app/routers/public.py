from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Image
from ..schemas import PublicImageOut
from ..storage import path_for

router = APIRouter(prefix="/public", tags=["public"])


def _shared_image(token: str, db: Session) -> Image:
    # Only images with a live share_token are reachable here; revoking makes this 404.
    image = db.scalar(select(Image).where(Image.share_token == token))
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is invalid or has been revoked")
    return image


@router.get("/{token}", response_model=PublicImageOut)
def get_shared_image(token: str, db: Session = Depends(get_db)) -> Image:
    return _shared_image(token, db)


@router.get("/{token}/file")
def get_shared_file(token: str, db: Session = Depends(get_db)) -> FileResponse:
    image = _shared_image(token, db)
    return FileResponse(path_for(image.stored_name), media_type=image.content_type)
