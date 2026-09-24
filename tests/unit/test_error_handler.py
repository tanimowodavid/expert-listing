import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.core.exceptions import (
    AppError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
)


def client_that_raises(error: Exception) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise error

    return TestClient(app)


@pytest.mark.parametrize(
    "error,expected_status",
    [
        (NotFoundError("missing"), 404),
        (ConflictError("clash"), 409),
        (InvalidReferenceError("bad reference"), 422),
    ],
)
def test_domain_errors_map_to_status_codes(error, expected_status):
    response = client_that_raises(error).get("/boom")

    assert response.status_code == expected_status
    assert response.json() == {"detail": error.message}


def test_unmapped_app_error_is_a_500_that_hides_its_message():
    response = client_that_raises(AppError("secret internal detail")).get("/boom")

    assert response.status_code == 500
    assert "secret" not in response.text