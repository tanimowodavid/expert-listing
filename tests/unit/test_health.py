from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


def use_db(fake_session):
    """Replace the real get_db dependency with one that yields a fake session."""

    def override():
        yield fake_session

    app.dependency_overrides[get_db] = override


def test_liveness_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_survives_a_database_outage(client):
    db = MagicMock()
    db.execute.side_effect = OperationalError("SELECT 1", {}, Exception("down"))
    use_db(db)

    response = client.get("/health")

    assert response.status_code == 200
    db.execute.assert_not_called()


def test_readiness_returns_ready_when_database_responds(client):
    db = MagicMock()
    use_db(db)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    db.execute.assert_called_once()


def test_readiness_returns_503_when_database_is_down(client):
    db = MagicMock()
    db.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )
    use_db(db)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_readiness_does_not_leak_internal_error_details(client):
    db = MagicMock()
    db.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("password authentication failed for user listings")
    )
    use_db(db)

    response = client.get("/health/ready")

    assert "password" not in response.text
    assert "listings" not in response.text