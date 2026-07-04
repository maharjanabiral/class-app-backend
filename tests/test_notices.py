import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import Role


@pytest.mark.asyncio
async def test_create_notice_broadcasts(client, mock_db):
    # Fake the notice that gets saved and returned
    fake_notice = MagicMock()
    fake_notice.id = 1
    fake_notice.title = "Exam tomorrow"
    fake_notice.body = "Prepare well"
    fake_notice.target_role = Role.student
    fake_notice.is_active = True
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    with patch("app.routers.notice.Notice") as MockNotice, \
         patch("app.routers.notice.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:

        MockNotice.return_value = fake_notice

        async with client as c:
            response = await c.post("/notices/", json={
                "title": "Exam tomorrow",
                "body": "Prepare well",
                "target_role": Role.student.value
            })

        assert response.status_code == 201
        mock_broadcast.assert_called_once_with(
            message={
                "type": "notice",
                "id": fake_notice.id,
                "title": fake_notice.title,
                "body": fake_notice.body,
                "target_role": Role.student.value
            },
            target_role=Role.student.value,
        )


@pytest.mark.asyncio
async def test_list_notices_returns_active(client, mock_db):
    fake_notice = MagicMock()
    fake_notice.id = 1
    fake_notice.title = "Holiday"
    fake_notice.body = "No school"
    fake_notice.is_active = True
    fake_notice.target_role = "student"
    fake_notice.create_at = "2026-01-01"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_notice]
    mock_db.execute = AsyncMock(return_value=mock_result)

    async with client as c:
        response = await c.get("/notices/")

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_deactivate_notice(client, mock_db):
    fake_notice = MagicMock()
    fake_notice.is_active = True
    mock_db.get = AsyncMock(return_value=fake_notice)

    async with client as c:
        response = await c.delete("/notices/1")

    assert response.status_code == 204
    assert fake_notice.is_active == False
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_notice_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    async with client as c:
        response = await c.delete("/notices/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Notice not found"


def test_websocket_connects_and_receives():
    with TestClient(app) as c:
        with c.websocket_connect("/notices/ws/student") as ws:
            # Trigger a broadcast from another thread/call if needed
            # For now just confirm the connection is accepted
            ws.send_text("ping")  # keep-alive message
