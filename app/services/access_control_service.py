from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.access_request import AccessRequest


class AccessResult:
    """Result of an access control check."""

    def __init__(self, allowed: bool, reason: str = "", redirect: str = ""):
        self.allowed = allowed
        self.reason = reason
        self.redirect = redirect


async def check_project_access(
    db: AsyncSession,
    project: Project,
    user: Optional[dict],
    password_unlocked: bool = False,
) -> AccessResult:
    """
    Check if a user can access a project.
    Returns an AccessResult with allowed=True/False and optional redirect.
    """
    # Step 1: Check password protection
    if project.password_hash and not password_unlocked:
        return AccessResult(
            allowed=False,
            reason="password_required",
            redirect=f"/{project.visible_path}/_unlock",
        )

    # Step 2: Check security level
    if project.security_level in (1, 2):
        # L1/L2: Public, no login needed
        return AccessResult(allowed=True)

    if project.security_level == 3:
        # L3: Requires login
        if not user:
            return AccessResult(
                allowed=False,
                reason="login_required",
                redirect="/login",
            )
        return AccessResult(allowed=True)

    if project.security_level == 4:
        # L4: Requires login + approved access request
        if not user:
            return AccessResult(
                allowed=False,
                reason="login_required",
                redirect="/login",
            )

        # Check if user has an approved access request
        result = await db.execute(
            select(AccessRequest).where(
                AccessRequest.project_id == project.id,
                AccessRequest.requester_id == user["id"],
                AccessRequest.status == "approved",
            ).limit(1)
        )
        approved = result.scalar_one_or_none()
        if approved:
            return AccessResult(allowed=True)

        # Check if there's a pending request
        result = await db.execute(
            select(AccessRequest).where(
                AccessRequest.project_id == project.id,
                AccessRequest.requester_id == user["id"],
                AccessRequest.status == "pending",
            ).limit(1)
        )
        pending = result.scalar_one_or_none()

        if pending:
            return AccessResult(
                allowed=False,
                reason="request_pending",
            )

        return AccessResult(
            allowed=False,
            reason="no_access",
        )

    return AccessResult(allowed=False, reason="unknown_level")


async def check_l4_access(
    db: AsyncSession,
    project_id: int,
    user_id: int,
) -> bool:
    """Check if a user has approved L4 access to a project."""
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.project_id == project_id,
            AccessRequest.requester_id == user_id,
            AccessRequest.status == "approved",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None
