import re
import os
import mimetypes
from pathlib import Path


def slugify(value: str) -> str:
    """Convert a string to a URL-safe slug."""
    value = value.lower().strip()
    value = re.sub(r'[^\w\-\u4e00-\u9fff]+', '-', value)
    value = re.sub(r'-+', '-', value)
    value = value.strip('-')
    return value


def validate_visible_path(path: str) -> bool:
    """Validate that a visible_path contains only safe characters."""
    if not path:
        return False
    # Allow: lowercase letters, numbers, hyphens, underscores, slashes, and Chinese chars
    return bool(re.match(r'^[a-z0-9_\-\/]+$', path))


def get_mime_type(filename: str) -> str:
    """Get MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    return "application/octet-stream"


def safe_path_join(base_dir: str, *paths: str) -> str:
    """Safely join path components, preventing directory traversal."""
    base = os.path.realpath(base_dir)
    full_path = os.path.realpath(os.path.join(base_dir, *paths))
    if not full_path.startswith(base):
        raise ValueError("Path traversal detected")
    return full_path


def ensure_dir(path: str) -> None:
    """Ensure a directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
