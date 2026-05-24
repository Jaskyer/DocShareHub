from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.access_request_service import approve_request, reject_request
from app.services.feishu_service import build_notification_card, send_message_card
from app.models.access_request import AccessRequest
from app.models.user import User
from app.models.project import Project

router = APIRouter(prefix="/api/feishu", tags=["feishu"])


@router.post("/webhook/card-action")
async def handle_card_action(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Feishu card action webhook (approve/reject button clicks).

    Feishu sends: { open_id, open_message_id, action { value } }
    """
    try:
        body = await request.json()
    except Exception:
        return {"code": -1, "msg": "Invalid JSON"}

    # Extract action info
    action = body.get("action", {})
    value = action.get("value", {})
    request_id = value.get("request_id")
    action_type = value.get("action")  # "approve" or "reject"

    if not request_id or not action_type:
        return {"code": -1, "msg": "Missing action data"}

    # Get the access request
    req = await db.get(AccessRequest, int(request_id))
    if not req:
        return {"code": -1, "msg": "Request not found"}

    if req.status != "pending":
        return {"code": -1, "msg": "Request already processed"}

    # Get the project creator
    project = await db.get(Project, req.project_id)
    if not project:
        return {"code": -1, "msg": "Project not found"}

    # Process the action
    if action_type == "approve":
        req.status = "approved"
        req.processed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        await db.commit()

        # Notify applicant
        applicant = await db.get(User, req.requester_id)
        if applicant:
            card = build_notification_card(
                project_name=project.name,
                approved=True,
                project_url=f"/{project.visible_path}",
            )
            await send_message_card(applicant.feishu_open_id, card)

        return {"code": 0, "msg": "Approved"}

    elif action_type == "reject":
        req.status = "rejected"
        req.processed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        await db.commit()

        # Notify applicant
        applicant = await db.get(User, req.requester_id)
        if applicant:
            card = build_notification_card(
                project_name=project.name,
                approved=False,
            )
            await send_message_card(applicant.feishu_open_id, card)

        return {"code": 0, "msg": "Rejected"}

    return {"code": -1, "msg": "Unknown action"}
