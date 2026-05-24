from typing import Optional

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.access_request import AccessRequestCreate
from app.services import access_request_service as ars
from app.services import project_service as ps
from app.services.feishu_service import (
    build_approval_card,
    build_notification_card,
    send_message_card,
)
from app.models.project import Project
from app.models.user import User
from app.utils.exceptions import UnauthorizedException, ForbiddenException, NotFoundException
from sqlalchemy import select

router = APIRouter(prefix="/api/projects", tags=["access-requests"])


def require_user(request: Request) -> dict:
    user = request.scope.get("user", None)
    if not user:
        raise UnauthorizedException("请先登录")
    return user


@router.post("/{project_id}/access-requests")
async def submit_access_request(
    project_id: int,
    request: Request,
    data: AccessRequestCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """Submit an L4 access request."""
    user = require_user(request)

    req = await ars.submit_request(
        db, project_id, user["id"],
        reason=data.reason if data else None,
    )

    # Send Feishu card to project creator
    project = await db.get(Project, project_id)
    if project and project.creator_id != user["id"]:
        creator = await db.get(User, project.creator_id)
        if creator and creator.feishu_open_id:
            card = build_approval_card(
                request_id=req.id,
                project_name=project.name,
                requester_name=user["feishu_name"],
                created_at=req.created_at.strftime("%Y-%m-%d %H:%M"),
            )
            message_id = await send_message_card(creator.feishu_open_id, card)
            if message_id:
                req.feishu_message_id = message_id
                await db.commit()

    return {"request": {"id": req.id, "status": req.status}}


@router.get("/{project_id}/access-requests")
async def list_access_requests(
    project_id: int,
    request: Request,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List access requests for a project (creator only)."""
    user = require_user(request)
    requests = await ars.get_requests(db, project_id, user["id"], status)
    return {"requests": requests}


@router.post("/{project_id}/access-requests/{request_id}/approve")
async def approve_access_request(
    project_id: int,
    request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Approve an access request."""
    user = require_user(request)
    req = await ars.approve_request(db, request_id, user["id"])

    # Send notification to applicant
    applicant = await db.get(User, req.requester_id)
    project = await db.get(Project, project_id)
    if applicant and project:
        card = build_notification_card(
            project_name=project.name,
            approved=True,
            project_url=f"/{project.visible_path}",
        )
        await send_message_card(applicant.feishu_open_id, card)

    return {"message": "已批准"}


@router.post("/{project_id}/access-requests/{request_id}/reject")
async def reject_access_request(
    project_id: int,
    request_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reject an access request."""
    user = require_user(request)
    req = await ars.reject_request(db, request_id, user["id"])

    # Send notification to applicant
    applicant = await db.get(User, req.requester_id)
    project = await db.get(Project, project_id)
    if applicant and project:
        card = build_notification_card(
            project_name=project.name,
            approved=False,
        )
        await send_message_card(applicant.feishu_open_id, card)

    return {"message": "已拒绝"}


@router.get("/{project_id}/access-status")
async def check_access_status(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Check current user's access status for a project."""
    user = require_user(request)
    status = await ars.get_my_request_status(db, project_id, user["id"])
    return {"status": status}
