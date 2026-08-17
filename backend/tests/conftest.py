"""Shared fixtures for the API suite.

The app builds its engine, settings and upload directory at import time, so the
environment has to point at throwaway locations *before* anything under `app.`
is imported. That happens at the top of this module, ahead of the app imports.
"""

import base64
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="gallery-tests-"))

os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_ROOT / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP_ROOT / "uploads")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# A real 1x1 PNG — the API sniffs nothing, but the bytes round-trip through
# storage and the file endpoints, so they should be genuine.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
GIF_1X1 = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_state():
    """Every test starts with an empty database and an empty upload directory."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    upload_dir = Path(settings.upload_dir)
    shutil.rmtree(upload_dir, ignore_errors=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def upload_dir() -> Path:
    return Path(settings.upload_dir)


@pytest.fixture
def png_bytes() -> bytes:
    return PNG_1X1


class UserSession:
    """A registered user plus the helpers a test needs to act as them."""

    def __init__(self, client: TestClient, email: str, password: str, data: dict):
        self._client = client
        self.email = email
        self.password = password
        self.id = data["user"]["id"]
        self.token = data["access_token"]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def upload(self, content: bytes = PNG_1X1, *, filename="pic.png",
               content_type="image/png", title="", description=""):
        return self._client.post(
            "/images",
            headers=self.headers,
            files={"file": (filename, content, content_type)},
            data={"title": title, "description": description},
        )

    def upload_ok(self, **kwargs) -> dict:
        response = self.upload(**kwargs)
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def make_user(client):
    """Register users on demand; each call returns a ready-to-use session."""
    counter = {"n": 0}

    def _make(email: str | None = None, password: str = "correct-horse-battery") -> UserSession:
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        response = client.post("/auth/register", json={"email": email, "password": password})
        assert response.status_code == 201, response.text
        return UserSession(client, email, password, response.json())

    return _make


@pytest.fixture
def alice(make_user) -> UserSession:
    return make_user("alice@example.com")


@pytest.fixture
def bob(make_user) -> UserSession:
    return make_user("bob@example.com")
