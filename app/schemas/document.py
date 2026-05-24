from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int]
    original_filename: str
    stored_path: str
    description: Optional[str] = None
    file_size: int
    mime_type: Optional[str]
    is_directory: bool
    is_renamed: bool
    is_deleted: bool = False
    is_visible: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdateRequest(BaseModel):
    description: Optional[str] = None
    is_visible: Optional[bool] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentTreeResponse(BaseModel):
    id: int
    original_filename: str
    is_directory: bool
    children: list["DocumentTreeResponse"] = []

    model_config = {"from_attributes": True}


class UrlRenameRequest(BaseModel):
    url_name: str = Field(..., pattern=r'^[a-zA-Z0-9_\-]+$', max_length=256)


class UrlMappingResponse(BaseModel):
    id: int
    project_id: int
    document_id: int
    url_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UrlMappingListResponse(BaseModel):
    mappings: list[UrlMappingResponse]


class UploadResponse(BaseModel):
    documents: list[dict]
