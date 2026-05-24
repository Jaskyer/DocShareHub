from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    project_id: int
    document_id: Optional[int] = None


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    document_id: Optional[int]
    project_name: Optional[str] = None
    project_visible_path: Optional[str] = None
    document_name: Optional[str] = None
    document_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    favorites: list[FavoriteResponse]
