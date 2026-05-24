from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document import UrlMappingResponse, UrlRenameRequest
from app.services import document_service as ds
from app.services.project_service import get_project
from app.utils.exceptions import UnauthorizedException, ForbiddenException

router = APIRouter(prefix="/api/projects", tags=["url-mappings"])


def require_user(request: Request) -> dict:
    user = request.scope.get("user", None)
    if not user:
        raise UnauthorizedException("请先登录")
    return user


@router.get("/{project_id}/url-mappings")
async def list_url_mappings(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all URL mappings for a project."""
    user = require_user(request)
    project = await get_project(db, project_id)
    if project.creator_id != user["id"]:
        raise ForbiddenException("无权操作此项目")
    mappings = await ds.get_url_mappings(db, project_id)
    return {"mappings": [UrlMappingResponse.model_validate(m) for m in mappings]}
