from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.template_setup import templates

router = APIRouter(tags=["pages"])


def _require_auth(request: Request):
    """Redirect to login if not authenticated."""
    user = request.scope.get("user", None)
    if not user:
        return RedirectResponse(url="/login")
    return None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request},
    )


@router.get("/my-projects", response_class=HTMLResponse)
async def my_projects(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/dashboard.html",
        {"request": request},
    )


@router.get("/my-projects/create", response_class=HTMLResponse)
async def create_project(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/create.html",
        {"request": request},
    )


@router.get("/my-projects/{project_id}/edit", response_class=HTMLResponse)
async def edit_project(request: Request, project_id: int):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/edit.html",
        {"request": request, "project_id": project_id},
    )


@router.get("/my-projects/{project_id}/upload", response_class=HTMLResponse)
async def upload_documents(request: Request, project_id: int):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/upload.html",
        {"request": request, "project_id": project_id},
    )


@router.get("/my-projects/{project_id}/url-rename", response_class=HTMLResponse)
async def url_rename(request: Request, project_id: int):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/url_rename.html",
        {"request": request, "project_id": project_id},
    )


@router.get("/my-projects/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/favorites.html",
        {"request": request},
    )


@router.get("/my-projects/{project_id}/access-requests", response_class=HTMLResponse)
async def access_requests_page(request: Request, project_id: int):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "my_projects/access_requests.html",
        {"request": request, "project_id": project_id},
    )
