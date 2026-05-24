from typing import Optional

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document import DocumentResponse, DocumentUpdateRequest, UrlRenameRequest
from app.services import document_service as ds
from app.services.project_service import get_project
from app.utils.exceptions import UnauthorizedException, ForbiddenException

router = APIRouter(prefix="/api/projects", tags=["documents"])


def require_user(request: Request) -> dict:
    user = request.scope.get("user", None)
    if not user:
        raise UnauthorizedException("请先登录")
    return user


async def check_project_owner(db: AsyncSession, project_id: int, user_id: int):
    """Check if user owns the project."""
    project = await get_project(db, project_id)
    if project.creator_id != user_id:
        raise ForbiddenException("无权操作此项目")
    return project


@router.post("/{project_id}/documents/upload")
async def upload_documents(
    project_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload files/folders to a project."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    results = await ds.upload_files(db, project_id, files)
    return {"documents": results}


@router.get("/{project_id}/documents")
async def list_documents(
    project_id: int,
    request: Request,
    parent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List documents in a project."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    documents = await ds.get_documents(db, project_id, parent_id)
    return {"documents": [DocumentResponse.model_validate(d) for d in documents]}


@router.get("/{project_id}/documents/tree")
async def get_document_tree(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get document tree (nested structure)."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    tree = await ds.get_document_tree(db, project_id)
    return {"tree": tree}


@router.delete("/{project_id}/documents/{document_id}")
async def delete_document(
    project_id: int,
    document_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    await ds.delete_document(db, project_id, document_id)
    return {"message": "文档已删除"}


@router.put("/{project_id}/documents/{document_id}")
async def update_document_details(
    project_id: int,
    document_id: int,
    request: Request,
    data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update document details (description, etc.)."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    doc = await ds.update_document(db, project_id, document_id, data.model_dump(exclude_unset=True))
    return {"document": DocumentResponse.model_validate(doc)}


@router.post("/{project_id}/documents/{document_id}/rename")
async def set_url_rename(
    project_id: int,
    document_id: int,
    request: Request,
    data: UrlRenameRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set/update URL rename for a document."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    mapping = await ds.set_url_rename(db, project_id, document_id, data.url_name)
    return {"mapping": {"id": mapping.id, "url_name": mapping.url_name}}


@router.delete("/{project_id}/documents/{document_id}/rename")
async def clear_url_rename(
    project_id: int,
    document_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Remove URL rename from a document."""
    user = require_user(request)
    await check_project_owner(db, project_id, user["id"])
    await ds.clear_url_rename(db, project_id, document_id)
    return {"message": "URL 重命名已清除"}
