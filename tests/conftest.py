import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    # Undo any dependency overrides so tests can't leak into each other
    app.dependency_overrides.clear()