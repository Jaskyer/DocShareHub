import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.template_setup import templates
from app.models.project import Project
from app.utils.rate_limiter import file_scan_limiter
from app.models.document import Document
from app.models.url_mapping import UrlMapping
from app.models.access_request import AccessRequest
from app.services import project_service as ps
from app.services.access_control_service import check_project_access
from app.services.storage_service import get_upload_dir
from app.utils.helpers import safe_path_join, get_mime_type

router = APIRouter(tags=["file-serve"])


@router.get("/no_permission", response_class=HTMLResponse)
async def no_permission_page(request: Request):
    """Generic no permission page."""
    return templates.TemplateResponse(
        "no_permission.html",
        {"request": request, "show_request_form": False},
    )


@router.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_project_path(
    request: Request,
    full_path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Catch-all route for serving project files.

    full_path = "docs" or "docs/subdir/file.html" or "docs/_unlock"
    First segment is always the project's visible_path.
    """
    is_head = request.method == "HEAD"
    full_path = full_path.rstrip("/")

    # Split path into segments
    parts = full_path.split("/") if full_path else []
    if not parts:
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    visible_path = parts[0]
    # Remaining path is the sub-path within the project files
    sub_path = "/".join(parts[1:]) if len(parts) > 1 else ""

    # Special route: _unlock (password entry)
    if sub_path == "_unlock":
        return await _password_unlock_page(request, visible_path, db)

    # Look up project
    project = await ps.get_project_by_path(db, visible_path)
    if not project:
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Check password unlock
    password_unlocked = _is_password_unlocked(request, project.id)

    # Check access control
    user = request.scope.get("user", None)
    access = await check_project_access(db, project, user, password_unlocked)

    if not access.allowed:
        if access.reason == "password_required":
            next_url = f"/{full_path}"
            return RedirectResponse(url=f"/{visible_path}/_unlock?next={next_url}")
        elif access.reason == "login_required":
            return RedirectResponse(url=f"/login?next=/{full_path}")
        elif access.reason == "no_access":
            return await _render_no_permission(request, db, project, user)
        elif access.reason == "request_pending":
            return templates.TemplateResponse(
                "no_permission.html",
                {
                    "request": request,
                    "project_id": project.id,
                    "project_name": project.name,
                    "show_request_form": False,
                    "request_status": "pending",
                },
                status_code=403,
            )
        else:
            return templates.TemplateResponse("error/403.html", {"request": request}, status_code=403)

    # == Access granted ==
    # Rate limit check for file scanning
    client_ip = request.client.host if request.client else "unknown"
    if not file_scan_limiter.check(f"scan:{client_ip}:{project.id}"):
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Too Many Requests", status_code=429)

    # Serve the requested path
    return await _serve_path(request, db, project, sub_path, is_head)


async def _password_unlock_page(request: Request, visible_path: str, db: AsyncSession):
    """Render password unlock page."""
    project = await ps.get_project_by_path(db, visible_path)
    if not project:
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    return templates.TemplateResponse(
        "password_unlock.html",
        {
            "request": request,
            "project_id": project.id,
            "project_name": project.name,
            "visible_path": visible_path,
        },
    )


async def _serve_path(
    request: Request,
    db: AsyncSession,
    project: Project,
    sub_path: str,
    is_head: bool = False,
):
    """Serve a file or directory within a project."""
    # If no sub-path, serve project root
    if not sub_path:
        return await _render_directory(db, project, "", request)

    # Try URL mapping first (match the first path segment as url_name)
    first_segment = sub_path.split("/")[0]
    remaining = "/".join(sub_path.split("/")[1:]) if "/" in sub_path else ""

    result = await db.execute(
        select(UrlMapping).where(
            UrlMapping.project_id == project.id,
            UrlMapping.url_name == first_segment,
        )
    )
    mapping = result.scalar_one_or_none()

    if mapping and not remaining:
        # URL mapping matched at root level - serve the mapped file
        doc = await db.get(Document, mapping.document_id)
        if doc and not doc.is_directory:
            file_path = safe_path_join(get_upload_dir(), doc.stored_path)
            if os.path.isfile(file_path):
                mime = doc.mime_type or get_mime_type(doc.original_filename)
                if is_head:
                    from fastapi.responses import Response
                    return Response(headers={"Content-Type": mime})
                return FileResponse(file_path, media_type=mime)
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Serve from actual filesystem path
    relative_file_path = os.path.join(str(project.id), "files", sub_path)
    abs_path = safe_path_join(get_upload_dir(), relative_file_path)

    if not os.path.exists(abs_path):
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Check if file was renamed (should block original path)
    if os.path.isfile(abs_path):
        normalized_path = relative_file_path.replace("\\", "/")
        result = await db.execute(
            select(Document).where(
                Document.project_id == project.id,
                Document.is_renamed == True,
            )
        )
        for doc in result.scalars().all():
            if doc.stored_path.replace("\\", "/") == normalized_path:
                return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Directory listing
    if os.path.isdir(abs_path):
        return await _render_directory(db, project, sub_path, request)

    # Serve file
    mime = get_mime_type(abs_path)
    if is_head:
        from fastapi.responses import Response
        return Response(headers={"Content-Type": mime})
    return FileResponse(abs_path, media_type=mime)


async def _render_directory(
    db: AsyncSession,
    project: Project,
    sub_path: str,
    request: Request,
):
    """Render a directory listing."""
    dir_path = os.path.join(get_upload_dir(), str(project.id), "files", sub_path)

    # Check for index.html
    index_path = os.path.join(dir_path, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html; charset=utf-8")

    if not os.path.isdir(dir_path):
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Security: if allow_listing is False, return 404 instead of showing files
    if not project.allow_listing:
        return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)

    # Build directory listing
    items = []

    # Pre-fetch URL mappings for renamed files in this project
    renamed_paths = {}
    result = await db.execute(
        select(Document, UrlMapping).join(
            UrlMapping, UrlMapping.document_id == Document.id
        ).where(
            Document.project_id == project.id,
            Document.is_renamed == True,
        )
    )
    for doc, mapping in result.all():
        renamed_paths[doc.stored_path.replace("\\", "/")] = mapping.url_name

    # Pre-fetch descriptions for all documents in this project
    doc_map = {}
    user = request.scope.get("user", None)
    is_owner = user and user["id"] == project.creator_id
    result = await db.execute(
        select(Document).where(
            Document.project_id == project.id,
            Document.is_deleted == False,
        )
    )
    for doc in result.scalars().all():
        doc_map[doc.stored_path.replace("\\", "/")] = {
            "description": doc.description or "",
            "id": doc.id,
            "is_visible": doc.is_visible,
        }

    try:
        for entry in sorted(os.listdir(dir_path), key=str.lower):
            full_entry = os.path.join(dir_path, entry)
            is_dir = os.path.isdir(full_entry)
            stat = os.stat(full_entry)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

            # Check if this file has a URL rename
            entry_stored_path = os.path.join(str(project.id), "files", sub_path, entry).replace("\\", "/")
            url_name = renamed_paths.get(entry_stored_path)

            # Skip hidden files for non-owners
            doc_info = doc_map.get(entry_stored_path, {})
            if not is_owner and doc_info.get("is_visible") is False:
                continue

            items.append({
                "name": entry,
                "display_name": url_name if url_name else entry,
                "is_directory": is_dir,
                "is_renamed": bool(url_name),
                "description": doc_map.get(entry_stored_path, {}).get("description", ""),
                "size": stat.st_size if not is_dir else 0,
                "size_str": _format_size(stat.st_size if not is_dir else 0),
                "modified_str": _format_datetime(mtime),
            })
    except PermissionError:
        pass

    items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))

    # Build breadcrumbs
    parts = [p for p in sub_path.split("/") if p]
    breadcrumbs = []
    cumulative = ""
    for part in parts:
        cumulative += "/" + part
        breadcrumbs.append({
            "name": part,
            "path": f"/{project.visible_path}{cumulative}",
        })

    return templates.TemplateResponse(
        "project_view.html",
        {
            "request": request,
            "project_name": project.name,
            "project_id": project.id,
            "visible_path": project.visible_path,
            "project": project,
            "current_path": sub_path,
            "items": items,
            "breadcrumbs": breadcrumbs,
            "user": user,
        },
    )


async def _render_no_permission(request, db, project, user):
    """Render the no-permission page."""
    show_form = False
    request_status = None

    if user:
        result = await db.execute(
            select(AccessRequest).where(
                AccessRequest.project_id == project.id,
                AccessRequest.requester_id == user["id"],
            ).order_by(AccessRequest.created_at.desc())
        )
        existing = result.scalar_one_or_none()
        if existing:
            request_status = existing.status
        else:
            show_form = True

    return templates.TemplateResponse(
        "no_permission.html",
        {
            "request": request,
            "project_id": project.id,
            "project_name": project.name,
            "visible_path": project.visible_path,
            "project_url": f"/{project.visible_path}",
            "show_request_form": show_form,
            "request_status": request_status,
        },
        status_code=403 if not show_form else 200,
    )


def _format_size(bytes_val: int) -> str:
    if not bytes_val:
        return "-"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(bytes_val)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}" if i > 0 else f"{int(size)} B"


def _format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _is_password_unlocked(request: Request, project_id: int) -> bool:
    unlocked = request.cookies.get("unlocked_projects", "")
    if not unlocked:
        return False
    return str(project_id) in unlocked.split(",")
