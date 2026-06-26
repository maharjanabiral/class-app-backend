from pydantic import BaseModel
from datetime import datetime
from app.models.notice import TargetRole


class NoticeCreate(BaseModel):
    title: str
    body: str
    target_role: TargetRole = TargetRole.all


class NoticeResponse(BaseModel):
    id: int
    title: str
    body: str
    target_role: TargetRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadNoticeCountResponse(BaseModel):
    count: int
