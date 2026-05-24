from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.database import async_session
from app.models.user import User

# Cache for tenant access token
_tenant_token_cache: dict = {"token": None, "expires_at": None}


def get_oauth_url(state: str = "state") -> str:
    """Build Feishu OAuth authorization URL."""
    params = urlencode({
        "redirect_uri": settings.feishu_oauth_redirect_uri,
        "app_id": settings.feishu_app_id,
        "state": state,
    })
    return f"https://open.feishu.cn/open-apis/authen/v1/authorize?{params}"


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for access token."""
    url = "https://open.feishu.cn/open-apis/authen/v1/access_token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "app_id": settings.feishu_app_id,
        "app_secret": settings.feishu_app_secret,
        "redirect_uri": settings.feishu_oauth_redirect_uri,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        body = resp.json()

    if body.get("code") != 0:
        raise Exception(f"Feishu access_token error: {body.get('msg', 'unknown')}")

    data = body.get("data", {})
    return data


async def get_user_info(access_token: str) -> dict:
    """Get user info using access token."""
    url = "https://open.feishu.cn/open-apis/authen/v1/user_info"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        body = resp.json()

    if body.get("code") != 0:
        raise Exception(f"Feishu user_info error: {body.get('msg', 'unknown')}")

    data = body.get("data", {})
    return data


async def get_tenant_token() -> Optional[str]:
    """Get tenant access token for bot API calls. Cached with 2-hour expiry."""
    now = datetime.now(timezone.utc)

    if _tenant_token_cache["token"] and _tenant_token_cache["expires_at"]:
        if now < _tenant_token_cache["expires_at"]:
            return _tenant_token_cache["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": settings.feishu_app_id,
        "app_secret": settings.feishu_app_secret,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    token = data.get("tenant_access_token")
    expire = data.get("expire", 7200)  # default 2 hours

    _tenant_token_cache["token"] = token
    _tenant_token_cache["expires_at"] = now + timedelta(seconds=expire - 300)  # 5min buffer

    return token


async def get_or_create_user(feishu_data: dict) -> User:
    """Get existing user or create new one from Feishu user info."""
    open_id = feishu_data.get("open_id") or feishu_data.get("sub", "")
    name = feishu_data.get("name", "")
    avatar = feishu_data.get("avatar_url", feishu_data.get("picture", ""))
    user_id = feishu_data.get("user_id", "")

    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.feishu_open_id == open_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.feishu_name = name
            if avatar:
                user.avatar_url = avatar
            if user_id:
                user.feishu_user_id = user_id
            user.last_login_at = datetime.now(timezone.utc)
        else:
            user = User(
                feishu_open_id=open_id,
                feishu_user_id=user_id,
                feishu_name=name,
                avatar_url=avatar or None,
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)
        return user


async def send_message_card(open_id: str, card_content: dict) -> Optional[str]:
    """Send a message card to a user. Returns message_id."""
    tenant_token = await get_tenant_token()
    if not tenant_token:
        return None

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": __import__("json").dumps(card_content),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("message_id")
    return None


def build_approval_card(request_id: int, project_name: str, requester_name: str, created_at: str) -> dict:
    """Build an approval card for the project creator."""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"访问申请: {project_name}"},
            "template": "blue",
        },
        "elements": [
            {"tag": "markdown", "content": f"**申请人:** {requester_name}\n**项目:** {project_name}\n**时间:** {created_at}"},
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "同意"},
                        "type": "primary",
                        "value": {"request_id": str(request_id), "action": "approve"},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "拒绝"},
                        "type": "danger",
                        "value": {"request_id": str(request_id), "action": "reject"},
                    },
                ],
            },
        ],
    }


def build_notification_card(project_name: str, approved: bool, project_url: str = "") -> dict:
    """Build a notification card for the applicant."""
    template = "green" if approved else "red"
    title = "访问已批准" if approved else "访问被拒绝"
    content = f"你的 **{project_name}** 访问申请已批准。\n[查看项目]({project_url})" if approved else f"你的 **{project_name}** 访问申请已被拒绝。如有疑问，请联系项目所属人。"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        },
        "elements": [
            {"tag": "markdown", "content": content},
        ],
    }
