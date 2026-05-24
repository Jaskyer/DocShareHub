import os
import mimetypes
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.models.document import Document
from app.models.url_mapping import UrlMapping
from app.services.storage_service import save_file, delete_file, delete_directory, move_to_recycle
from app.utils.exceptions import NotFoundException, BadRequestException
from app.utils.helpers import get_mime_type


async def upload_files(
    db: AsyncSession,
    project_id: int,
    files: list[UploadFile],
) -> list[dict]:
    """Upload multiple files to a project, preserving folder structure."""
    results = []

    for upload_file in files:
        try:
            # Get the relative path (webkitdirectory gives full path, otherwise just filename)
            filename = upload_file.filename or "unnamed"
            # Normalize path separators
            relative_path = filename.replace("\\", "/").lstrip("/")

            content = await upload_file.read()
            file_size = len(content)

            # Determine parent path
            parent_dir = None
            parent_id = None
            if "/" in relative_path:
                parts = relative_path.split("/")
                # Create directory records for each level
                current_parent = None
                for i, part in enumerate(parts[:-1]):
                    dir_path = "/".join(parts[:i+1]) + "/"
                    # Check if directory record exists
                    result = await db.execute(
                        select(Document).where(
                            Document.project_id == project_id,
                            Document.stored_path == os.path.join(str(project_id), "files", dir_path),
                            Document.is_directory == True,
                        )
                    )
                    dir_doc = result.scalar_one_or_none()
                    if not dir_doc:
                        dir_path_full = os.path.join(str(project_id), "files", dir_path)
                        dir_doc = Document(
                            project_id=project_id,
                            parent_id=current_parent,
                            original_filename=part + "/",
                            stored_path=dir_path_full,
                            file_size=0,
                            mime_type="inode/directory",
                            is_directory=True,
                        )
                        db.add(dir_doc)
                        await db.flush()
                    current_parent = dir_doc.id
                parent_id = current_parent

            # Save file to disk
            stored_path = await save_file(project_id, relative_path, content)

            # Check for duplicates
            existing = await db.execute(
                select(Document).where(
                    Document.project_id == project_id,
                    Document.stored_path == stored_path,
                )
            )
            if existing.scalar_one_or_none():
                # Remove duplicate and skip
                await delete_file(stored_path)
                results.append({
                    "original_filename": relative_path,
                    "file_size": file_size,
                    "error": "文件已存在",
                })
                continue

            # Determine mime type
            mime = get_mime_type(relative_path)

            # Create document record
            doc = Document(
                project_id=project_id,
                parent_id=parent_id,
                original_filename=os.path.basename(relative_path),
                stored_path=stored_path,
                file_size=file_size,
                mime_type=mime,
                is_directory=False,
            )
            db.add(doc)
            await db.flush()

            results.append({
                "id": doc.id,
                "original_filename": relative_path,
                "file_size": file_size,
                "mime_type": mime,
            })

        except Exception as e:
            results.append({
                "original_filename": upload_file.filename or "unnamed",
                "error": str(e),
            })

    await db.commit()
    return results


async def get_documents(db: AsyncSession, project_id: int, parent_id: Optional[int] = None) -> list[Document]:
    """List documents in a project, optionally filtered by parent."""
    query = select(Document).where(
        Document.project_id == project_id,
        Document.is_directory == False,
        Document.is_deleted == False,
    ).order_by(Document.created_at.desc())

    if parent_id is not None:
        query = query.where(Document.parent_id == parent_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_document_tree(db: AsyncSession, project_id: int, parent_id: Optional[int] = None) -> list[dict]:
    """Get documents as a nested tree structure."""
    query = select(Document).where(
        Document.project_id == project_id,
    ).order_by(Document.original_filename)

    result = await db.execute(query)
    documents = result.scalars().all()

    # Build tree
    tree = []
    doc_map = {}
    for doc in documents:
        doc_map[doc.id] = {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "is_directory": doc.is_directory,
            "children": [],
        }

    for doc in documents:
        if doc.parent_id and doc.parent_id in doc_map:
            doc_map[doc.parent_id]["children"].append(doc_map[doc.id])
        elif parent_id is None or doc.parent_id == parent_id:
            tree.append(doc_map[doc.id])

    return tree


async def delete_document(db: AsyncSession, project_id: int, document_id: int) -> bool:
    """Soft-delete a document: move file to recycle bin and mark as deleted."""
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise NotFoundException("文档不存在")

    if doc.is_directory:
        # Recycle all children first
        children_result = await db.execute(
            select(Document).where(
                Document.parent_id == document_id,
                Document.is_deleted == False,
            )
        )
        for child in children_result.scalars().all():
            await delete_document(db, project_id, child.id)

        # Move directory to recycle
        await move_to_recycle(doc.stored_path)
    else:
        # Move file to recycle bin
        await move_to_recycle(doc.stored_path)

    # Soft-delete the document record
    doc.is_deleted = True
    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def update_document(db: AsyncSession, project_id: int, document_id: int, data: dict) -> Document:
    """Update document details (description, etc.)."""
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise NotFoundException("文档不存在")

    if "description" in data:
        doc.description = data["description"]
    if "is_visible" in data:
        doc.is_visible = data["is_visible"]

    doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def set_url_rename(db: AsyncSession, project_id: int, document_id: int, url_name: str) -> UrlMapping:
    """Set or update a URL rename for a document."""
    # Verify document exists
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise NotFoundException("文档不存在")

    # Check url_name uniqueness within project
    existing = await db.execute(
        select(UrlMapping).where(
            UrlMapping.project_id == project_id,
            UrlMapping.url_name == url_name,
            UrlMapping.document_id != document_id,
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(f"URL 名称 '{url_name}' 已被使用")

    # Check if rename already exists
    result = await db.execute(
        select(UrlMapping).where(UrlMapping.document_id == document_id)
    )
    mapping = result.scalar_one_or_none()

    if mapping:
        mapping.url_name = url_name
    else:
        mapping = UrlMapping(
            project_id=project_id,
            document_id=document_id,
            url_name=url_name,
        )
        db.add(mapping)

    # Mark document as renamed
    doc.is_renamed = True

    await db.commit()
    await db.refresh(mapping)
    return mapping


async def clear_url_rename(db: AsyncSession, project_id: int, document_id: int):
    """Remove a URL rename from a document."""
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise NotFoundException("文档不存在")

    await db.execute(
        delete(UrlMapping).where(UrlMapping.document_id == document_id)
    )
    doc.is_renamed = False
    await db.commit()


async def get_url_mappings(db: AsyncSession, project_id: int) -> list[UrlMapping]:
    """Get all URL mappings for a project."""
    result = await db.execute(
        select(UrlMapping).where(
            UrlMapping.project_id == project_id
        ).order_by(UrlMapping.created_at.desc())
    )
    return list(result.scalars().all())
