from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.favorite import FavoriteCreate
from app.services import favorite_service as fs
from app.utils.exceptions import UnauthorizedException

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


def require_user(request: Request) -> dict:
    user = request.scope.get("user", None)
    if not user:
        raise UnauthorizedException("请先登录")
    return user


@router.get("")
async def list_favorites(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List current user's favorites."""
    user = require_user(request)
    favorites = await fs.list_favorites(db, user["id"])
    return {"favorites": favorites}


@router.post("")
async def add_favorite(
    request: Request,
    data: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a favorite."""
    user = require_user(request)
    fav = await fs.add_favorite(db, user["id"], data.project_id, data.document_id)
    return {"favorite": {"id": fav.id}}


@router.delete("/{favorite_id}")
async def remove_favorite(
    favorite_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Remove a favorite."""
    user = require_user(request)
    await fs.remove_favorite(db, favorite_id, user["id"])
    return {"message": "已取消收藏"}
