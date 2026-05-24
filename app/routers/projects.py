from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, PasswordVerifyRequest
from app.services import project_service as ps
from app.utils.exceptions import UnauthorizedException, ForbiddenException

router = APIRouter(prefix="/api/projects", tags=["projects"])


def require_user(request: Request) -> dict:
    """Dependency to require authenticated user."""
    user = request.scope.get("user", None)
    if not user:
        raise UnauthorizedException("请先登录")
    return user


@router.get("/public")
async def list_public_projects(db: AsyncSession = Depends(get_db)):
    """List all public L1/L2 projects."""
    projects = await ps.get_public_projects(db)
    result = []
    for p in projects:
        count = await ps.get_document_count(db, p.id)
        result.append(ps.project_to_response(p, doc_count=count))
    return {"projects": result}


@router.get("")
async def list_my_projects(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List projects owned by current user."""
    user = require_user(request)
    projects = await ps.get_user_projects(db, user["id"])
    result = []
    for p in projects:
        count = await ps.get_document_count(db, p.id)
        result.append(ps.project_to_response(p, count))
    return {"projects": result}


@router.post("")
async def create_project(
    request: Request,
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    user = require_user(request)
    project = await ps.create_project(db, user["id"], data)
    return {"project": ps.project_to_response(project)}


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get project details."""
    user = require_user(request)
    project = await ps.get_project(db, project_id)
    if project.creator_id != user["id"]:
        raise ForbiddenException("无权访问此项目")
    count = await ps.get_document_count(db, project.id)
    return {"project": ps.project_to_response(project, count)}


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    request: Request,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    user = require_user(request)
    project = await ps.update_project(db, project_id, user["id"], data)
    return {"project": ps.project_to_response(project)}


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project."""
    user = require_user(request)
    await ps.delete_project(db, project_id, user["id"])
    return {"message": "项目已删除"}


@router.post("/{project_id}/verify-password")
async def verify_project_password(
    project_id: int,
    data: PasswordVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify project password and set session cookie."""
    # Rate limiting: max 5 attempts per 5 minutes per IP+project
    client_ip = request.client.host if request.client else "unknown"
    from app.utils.rate_limiter import password_limiter
    limit_key = f"pw:{client_ip}:{project_id}"
    if not password_limiter.check(limit_key):
        from app.utils.exceptions import BadRequestException
        raise BadRequestException("尝试次数过多，请5分钟后再试")

    valid = await ps.verify_project_password(db, project_id, data.password)
    if not valid:
        raise ForbiddenException("密码错误")

    from fastapi.responses import JSONResponse
    resp = JSONResponse({"verified": True})
    # Store unlocked status in a cookie
    unlocked = request.cookies.get("unlocked_projects", "")
    project_ids = set(unlocked.split(",")) if unlocked else set()
    project_ids.add(str(project_id))
    resp.set_cookie(
        key="unlocked_projects",
        value=",".join(project_ids),
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax",
    )
    return resp


@router.get("/by-path/{visible_path:path}")
async def get_project_by_path(
    visible_path: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup project by visible_path (public info)."""
    project = await ps.get_project_by_path(db, visible_path)
    if not project:
        from app.utils.exceptions import NotFoundException
        raise NotFoundException("项目不存在")
    return {"project": ps.project_to_response(project)}
