from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.services.auth_service import verify_session_token
from app.database import async_session
from app.models.user import User
from sqlalchemy import select


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract JWT from cookie and attach user to request scope."""

    async def dispatch(self, request: Request, call_next):
        # Store user in scope (shared between middleware and route handler)
        request.scope["user"] = None

        token = request.cookies.get("auth_token")
        if token:
            payload = verify_session_token(token)
            if payload:
                user_id = payload.get("user_id")
                if user_id:
                    async with async_session() as session:
                        result = await session.execute(
                            select(User).where(User.id == user_id)
                        )
                        user = result.scalar_one_or_none()
                        if user:
                            request.scope["user"] = {
                                "id": user.id,
                                "feishu_open_id": user.feishu_open_id,
                                "feishu_name": user.feishu_name,
                                "avatar_url": user.avatar_url,
                            }

        response = await call_next(request)
        return response
