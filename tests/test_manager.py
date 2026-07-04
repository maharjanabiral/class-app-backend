# tests/test_connection_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.websocket import ConnectionManager

@pytest.fixture
def manager():
    return ConnectionManager()

def make_ws():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws

@pytest.mark.asyncio
async def test_connect_adds_to_all_and_role(manager):
    ws = make_ws()
    await manager.connect(ws, "teacher")

    assert ws in manager.active_connections["all"]
    assert ws in manager.active_connections["teacher"]
    assert ws not in manager.active_connections["student"]

@pytest.mark.asyncio
async def test_disconnect_removes_from_all_buckets(manager):
    ws = make_ws()
    await manager.connect(ws, "student")
    manager.disconnect(ws, "student")

    assert ws not in manager.active_connections["all"]
    assert ws not in manager.active_connections["student"]

@pytest.mark.asyncio
async def test_broadcast_sends_to_role(manager):
    ws1, ws2 = make_ws(), make_ws()
    await manager.connect(ws1, "teacher")
    await manager.connect(ws2, "student")

    await manager.broadcast({"msg": "hello"}, "teacher")

    ws1.send_json.assert_called_once_with({"msg": "hello"})
    ws2.send_json.assert_not_called()

@pytest.mark.asyncio
async def test_broadcast_purges_dead_connections(manager):
    ws = make_ws()
    ws.send_json = AsyncMock(side_effect=Exception("disconnected"))
    await manager.connect(ws, "student")

    await manager.broadcast({"msg": "notice"}, "student")

    # Dead socket should be purged from all buckets
    assert ws not in manager.active_connections["all"]
    assert ws not in manager.active_connections["student"]
