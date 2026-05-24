from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AccessRequestCreate(BaseModel):
    reason: Optional[str] = None


class AccessRequestResponse(BaseModel):
    id: int
    project_id: int
    requester_id: int
    requester_name: Optional[str] = None
    status: str
    reason: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AccessRequestListResponse(BaseModel):
    requests: list[AccessRequestResponse]


class AccessStatusResponse(BaseModel):
    status: str  # none | pending | approved | rejected
