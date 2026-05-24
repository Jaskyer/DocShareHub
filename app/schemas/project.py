from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=256)
    description: Optional[str] = None
    visible_path: str = Field(..., pattern=r'^[a-z0-9_\-/]+$', max_length=256)
    security_level: int = Field(default=1, ge=1, le=4)
    password: Optional[str] = Field(None, min_length=4)
    allow_listing: bool = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = None
    visible_path: Optional[str] = Field(None, pattern=r'^[a-z0-9_\-/]+$', max_length=256)
    security_level: Optional[int] = Field(None, ge=1, le=4)
    password: Optional[str] = None  # None = keep, "" = clear, otherwise set new
    allow_listing: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    visible_path: str
    security_level: int
    has_password: bool
    allow_listing: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class PasswordVerifyRequest(BaseModel):
    password: str
