from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import Favorite
from app.models.project import Project
from app.models.document import Document
from app.utils.exceptions import NotFoundException, BadRequestException


async def add_favorite(
    db: AsyncSession,
    user_id: int,
    project_id: int,
    document_id: Optional[int] = None,
) -> Favorite:
    """Add a favorite."""
    # Check existing
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.project_id == project_id,
            Favorite.document_id == document_id,
        )
    )
    if result.scalar_one_or_none():
        raise BadRequestException("已经收藏过了")

    fav = Favorite(
        user_id=user_id,
        project_id=project_id,
        document_id=document_id,
    )
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


async def remove_favorite(db: AsyncSession, favorite_id: int, user_id: int):
    """Remove a favorite."""
    fav = await db.get(Favorite, favorite_id)
    if not fav or fav.user_id != user_id:
        raise NotFoundException("收藏不存在")
    await db.delete(fav)
    await db.commit()


async def list_favorites(db: AsyncSession, user_id: int) -> list[dict]:
    """List all favorites for a user with project/document info."""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
        ).order_by(Favorite.created_at.desc())
    )
    favorites = result.scalars().all()

    enriched = []
    for fav in favorites:
        project = await db.get(Project, fav.project_id)
        doc_name = None
        doc_path = None
        if fav.document_id:
            doc = await db.get(Document, fav.document_id)
            if doc:
                doc_name = doc.original_filename
                # For the document path, strip the project/files/ prefix
                stored = doc.stored_path
                if "/files/" in stored:
                    doc_path = stored.split("/files/", 1)[1]

        enriched.append({
            "id": fav.id,
            "user_id": fav.user_id,
            "project_id": fav.project_id,
            "document_id": fav.document_id,
            "project_name": project.name if project else None,
            "project_visible_path": project.visible_path if project else None,
            "document_name": doc_name,
            "document_path": doc_path,
            "created_at": fav.created_at,
        })
    return enriched
