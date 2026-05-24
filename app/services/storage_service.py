import os
import shutil
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.utils.helpers import safe_path_join, ensure_dir


def get_upload_dir() -> str:
    """Get the absolute upload directory path."""
    return os.path.abspath(settings.upload_dir)


def get_project_dir(project_id: int) -> str:
    """Get the storage directory for a project."""
    project_dir = os.path.join(get_upload_dir(), str(project_id), "files")
    ensure_dir(project_dir)
    return project_dir


def get_file_path(project_id: int, stored_path: str) -> str:
    """Get the absolute path for a stored file."""
    base_dir = get_upload_dir()
    return safe_path_join(base_dir, stored_path)


async def save_file(project_id: int, relative_path: str, content: bytes) -> str:
    """Save a file to disk. Returns the stored_path (relative to uploads dir)."""
    stored_path = os.path.join(str(project_id), "files", relative_path)
    abs_path = get_file_path(project_id, stored_path)

    # Ensure parent directory exists
    ensure_dir(os.path.dirname(abs_path))

    # Write file
    with open(abs_path, "wb") as f:
        f.write(content)

    return stored_path


def get_recycle_dir(project_id: int) -> str:
    """Get the recycle bin directory for a project."""
    recycle_dir = os.path.join(get_upload_dir(), str(project_id), ".recycle")
    ensure_dir(recycle_dir)
    return recycle_dir


async def move_to_recycle(stored_path: str) -> str:
    """Move a file to the project's recycle bin. Returns the recycle path."""
    abs_path = safe_path_join(get_upload_dir(), stored_path)
    if not os.path.exists(abs_path):
        return ""
    # Determine recycle path
    project_id = stored_path.split("/")[0]
    recycle_dir = get_recycle_dir(project_id)
    # Preserve relative path structure within recycle bin
    rel_path = stored_path.replace("files", ".recycle", 1) if "/files/" in stored_path else os.path.join(".recycle", os.path.basename(stored_path))
    recycle_path = safe_path_join(get_upload_dir(), rel_path)
    ensure_dir(os.path.dirname(recycle_path))
    shutil.move(abs_path, recycle_path)
    return rel_path


async def restore_from_recycle(recycle_path: str) -> bool:
    """Restore a file from recycle bin back to its original location."""
    abs_recycle = safe_path_join(get_upload_dir(), recycle_path)
    original_path = recycle_path.replace(".recycle", "files", 1)
    abs_original = safe_path_join(get_upload_dir(), original_path)
    ensure_dir(os.path.dirname(abs_original))
    if os.path.exists(abs_recycle):
        shutil.move(abs_recycle, abs_original)
        return True
    return False


async def delete_file(stored_path: str) -> bool:
    """Delete a file from disk."""
    abs_path = safe_path_join(get_upload_dir(), stored_path)
    if os.path.isfile(abs_path):
        os.remove(abs_path)
        return True
    return False


async def delete_directory(stored_path: str) -> bool:
    """Recursively delete a directory from disk."""
    abs_path = safe_path_join(get_upload_dir(), stored_path)
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
        return True
    return False


def file_exists(stored_path: str) -> bool:
    """Check if a file exists on disk."""
    abs_path = safe_path_join(get_upload_dir(), stored_path)
    return os.path.exists(abs_path)
