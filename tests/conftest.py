import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.dependencies import get_current_admin, get_current_user
from app.database import get_db

# ── Fake DB session ───────────────────────────────────────────────────────────
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db

# ── Fake users ────────────────────────────────────────────────────────────────
@pytest.fixture
def fake_admin():
    user = MagicMock()
    user.id = 1
    user.role = "admin"
    return user

@pytest.fixture
def fake_user():
    user = MagicMock()
    user.id = 2
    user.role = "student"
    return user

# ── App client with overrides ─────────────────────────────────────────────────
@pytest.fixture
def client(mock_db, fake_admin, fake_user):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_admin] = lambda: fake_admin
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()
