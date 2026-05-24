import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.config import settings
from app.services.auth_service import create_session_token
from app.services.feishu_service import get_oauth_url, exchange_code, get_user_info, get_or_create_user
from app.template_setup import templates

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login")
async def login_redirect(request: Request, next: str = None):
    """Redirect to Feishu OAuth page."""
    state = secrets.token_urlsafe(16)
    oauth_url = get_oauth_url(state=state)
    response = RedirectResponse(url=oauth_url)
    # Store state in cookie for CSRF validation (simplified)
    response.set_cookie(key="oauth_state", value=state, httponly=True, max_age=300)
    if next:
        response.set_cookie(key="oauth_next", value=next, httponly=True, max_age=300, samesite="lax")
    return response


@router.get("/callback")
async def auth_callback(request: Request, code: str, state: str = None):
    """Handle Feishu OAuth callback."""
    try:
        # Exchange code for token
        token_data = await exchange_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        # Get user info
        user_info = await get_user_info(access_token)

        # Get or create user in database
        user = await get_or_create_user(user_info)

        # Create session token
        session_token = create_session_token(user.id, user.feishu_open_id)

        # Redirect to frontend with cookie
        next_url = request.cookies.get("oauth_next") or "/"
        response = RedirectResponse(url=next_url)
        response.set_cookie(
            key="auth_token",
            value=session_token,
            httponly=True,
            max_age=settings.jwt_expiry_hours * 3600,
            samesite="lax",
        )
        response.delete_cookie(key="oauth_next")
        return response
    except Exception as e:
        return RedirectResponse(url=f"/login?error={str(e)}")


@router.get("/logout")
async def logout():
    """Clear auth cookie."""
    response = RedirectResponse(url="/")
    response.delete_cookie(key="auth_token")
    return response


@router.get("/me")
async def get_current_user(request: Request):
    """Return current user info if authenticated."""
    user = request.scope.get("user", None)
    if user:
        return {"user": user}
    return {"user": None}


@router.get("/status")
async def auth_status(request: Request):
    """Return authentication status."""
    user = request.scope.get("user", None)
    if user:
        return {"authenticated": True, "user": user}
    return {"authenticated": False, "user": None}
