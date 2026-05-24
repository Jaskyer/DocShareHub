from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.document import Document
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.auth_service import hash_password, verify_password
from app.utils.exceptions import NotFoundException, BadRequestException, ForbiddenException


async def create_project(db: AsyncSession, user_id: int, data: ProjectCreate) -> Project:
    """Create a new project."""
    # Check visible_path uniqueness
    existing = await db.execute(
        select(Project).where(Project.visible_path == data.visible_path)
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(f"可见路径 '{data.visible_path}' 已被使用")

    password_hash = None
    if data.password:
        password_hash = hash_password(data.password)

    project = Project(
        creator_id=user_id,
        name=data.name,
        description=data.description,
        visible_path=data.visible_path,
        security_level=data.security_level,
        password_hash=password_hash,
        allow_listing=data.allow_listing,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: int) -> Project:
    """Get project by ID."""
    project = await db.get(Project, project_id)
    if not project or not project.is_active:
        raise NotFoundException("项目不存在")
    return project


async def get_project_by_path(db: AsyncSession, visible_path: str) -> Optional[Project]:
    """Get active project by visible_path."""
    result = await db.execute(
        select(Project).where(
            Project.visible_path == visible_path,
            Project.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_user_projects(db: AsyncSession, user_id: int) -> list[Project]:
    """Get all projects for a user."""
    result = await db.execute(
        select(Project).where(
            Project.creator_id == user_id,
            Project.is_active == True,
        ).order_by(Project.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_public_projects(db: AsyncSession) -> list[Project]:
    """Get all L1/L2 projects."""
    result = await db.execute(
        select(Project).where(
            Project.security_level.in_([1, 2]),
            Project.is_active == True,
        ).order_by(Project.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_project(db: AsyncSession, project_id: int, user_id: int, data: ProjectUpdate) -> Project:
    """Update a project."""
    project = await get_project(db, project_id)
    if project.creator_id != user_id:
        raise ForbiddenException("无权修改此项目")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.visible_path is not None and data.visible_path != project.visible_path:
        existing = await db.execute(
            select(Project).where(
                Project.visible_path == data.visible_path,
                Project.id != project_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException(f"可见路径 '{data.visible_path}' 已被使用")
        project.visible_path = data.visible_path
    if data.security_level is not None:
        project.security_level = data.security_level
    if data.allow_listing is not None:
        project.allow_listing = data.allow_listing
    if data.password is not None:
        if data.password == "":
            project.password_hash = None
        else:
            project.password_hash = hash_password(data.password)

    project.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: int, user_id: int):
    """Delete a project (soft delete)."""
    project = await get_project(db, project_id)
    if project.creator_id != user_id:
        raise ForbiddenException("无权删除此项目")

    project.is_active = False
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()


def project_to_response(project: Project, doc_count: int = 0) -> ProjectResponse:
    """Convert a Project model to a Pydantic response."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        visible_path=project.visible_path,
        security_level=project.security_level,
        has_password=bool(project.password_hash),
        allow_listing=project.allow_listing,
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=doc_count,
    )


async def get_document_count(db: AsyncSession, project_id: int) -> int:
    """Get count of non-directory documents in a project."""
    result = await db.execute(
        select(func.count(Document.id)).where(
            Document.project_id == project_id,
            Document.is_directory == False,
            Document.is_deleted == False,
        )
    )
    return result.scalar() or 0


async def verify_project_password(db: AsyncSession, project_id: int, password: str) -> bool:
    """Verify a project's password."""
    project = await get_project(db, project_id)
    if not project.password_hash:
        return True  # No password set
    return verify_password(password, project.password_hash)
