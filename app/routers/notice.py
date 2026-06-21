from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List

from app.database import get_db
from app.models.notice import Notice
from app.models.user import User
from app.schemas.notice import NoticeCreate, NoticeResponse
from app.dependencies import get_current_admin, get_current_user
from app.services.websocket import manager

router = APIRouter(prefix="/notices", tags=["Notices"])
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ─── WebSocket: clients connect here to receive notices ──────────────────────

@router.websocket("/ws/{role}")
async def notice_websocket(websocket: WebSocket, role: str):
    await manager.connect(websocket, role)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, role)


# ─── ADMIN: Create and broadcast a notice ────────────────────────────────────

@router.post(
    "/",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Broadcast a notice (Admin only)",
)
async def create_notice(
    data: NoticeCreate,
    db: DBSession,
    _=Depends(get_current_admin),
):
    notice = Notice(**data.model_dump())
    db.add(notice)
    await db.commit()
    await db.refresh(notice)

    # Push to connected clients
    await manager.broadcast(
        message={
            "type": "notice",
            "id": notice.id,
            "title": notice.title,
            "body": notice.body,
            "target_role": notice.target_role.value,
        },
        target_role=notice.target_role.value,
    )
    return notice


# ─── List all active notices ──────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[NoticeResponse],
    summary="List all active notices",
)
async def list_notices(
    db: DBSession,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notice)
        .order_by(Notice.created_at.desc())
    )
    return result.scalars().all()


# ─── ADMIN: Deactivate a notice ───────────────────────────────────────────────

@router.delete(
    "/{notice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a notice (Admin only)",
)
async def deactivate_notice(
    notice_id: int,
    db: DBSession,
    _=Depends(get_current_admin),
):
    notice = await db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    notice.is_active = False
    await db.commit()


@router.delete(
    "/{notice_id}/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a notice (Admin only)",
)
async def delete_notice(
    notice_id: int,
    db: DBSession,
    _=Depends(get_current_admin),
):
    notice = await db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await db.delete(notice)
    await db.commit()
