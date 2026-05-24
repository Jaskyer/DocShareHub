from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_request import AccessRequest
from app.models.user import User
from app.models.project import Project
from app.utils.exceptions import NotFoundException, BadRequestException, ForbiddenException


async def submit_request(
    db: AsyncSession,
    project_id: int,
    requester_id: int,
    reason: Optional[str] = None,
) -> AccessRequest:
    """Submit an L4 access request."""
    # Check for existing pending request
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.project_id == project_id,
            AccessRequest.requester_id == requester_id,
            AccessRequest.status == "pending",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise BadRequestException("已有待审批的访问申请")

    # Check for existing approved request
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.project_id == project_id,
            AccessRequest.requester_id == requester_id,
            AccessRequest.status == "approved",
        )
    )
    approved = result.scalar_one_or_none()
    if approved:
        raise BadRequestException("已有已批准的访问申请")

    request = AccessRequest(
        project_id=project_id,
        requester_id=requester_id,
        status="pending",
        reason=reason,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def get_requests(
    db: AsyncSession,
    project_id: int,
    creator_id: int,
    status_filter: Optional[str] = None,
) -> list[dict]:
    """Get access requests for a project (creator only)."""
    project = await db.get(Project, project_id)
    if not project or project.creator_id != creator_id:
        raise ForbiddenException("无权查看此项目的访问申请")

    query = select(AccessRequest).where(
        AccessRequest.project_id == project_id,
    )
    if status_filter:
        query = query.where(AccessRequest.status == status_filter)
    query = query.order_by(AccessRequest.created_at.desc())

    result = await db.execute(query)
    requests = result.scalars().all()

    # Enrich with requester names
    enriched = []
    for req in requests:
        user = await db.get(User, req.requester_id)
        enriched.append({
            "id": req.id,
            "project_id": req.project_id,
            "requester_id": req.requester_id,
            "requester_name": user.feishu_name if user else "Unknown",
            "status": req.status,
            "reason": req.reason,
            "created_at": req.created_at,
            "processed_at": req.processed_at,
        })
    return enriched


async def get_my_request_status(
    db: AsyncSession,
    project_id: int,
    requester_id: int,
) -> str:
    """Get the current user's access request status for a project."""
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.project_id == project_id,
            AccessRequest.requester_id == requester_id,
        ).order_by(AccessRequest.created_at.desc())
    )
    req = result.scalar_one_or_none()
    if not req:
        return "none"
    return req.status


async def approve_request(
    db: AsyncSession,
    request_id: int,
    creator_id: int,
) -> AccessRequest:
    """Approve an access request."""
    req = await db.get(AccessRequest, request_id)
    if not req:
        raise NotFoundException("申请不存在")
    if req.status != "pending":
        raise BadRequestException("该申请已经处理过了")

    project = await db.get(Project, req.project_id)
    if not project or project.creator_id != creator_id:
        raise ForbiddenException("无权处理此申请")

    req.status = "approved"
    req.processor_id = creator_id
    req.processed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)
    return req


async def reject_request(
    db: AsyncSession,
    request_id: int,
    creator_id: int,
) -> AccessRequest:
    """Reject an access request."""
    req = await db.get(AccessRequest, request_id)
    if not req:
        raise NotFoundException("申请不存在")
    if req.status != "pending":
        raise BadRequestException("该申请已经处理过了")

    project = await db.get(Project, req.project_id)
    if not project or project.creator_id != creator_id:
        raise ForbiddenException("无权处理此申请")

    req.status = "rejected"
    req.processor_id = creator_id
    req.processed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)
    return req
