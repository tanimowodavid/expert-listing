from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.errors import register_exception_handlers
from app.core.exceptions import (
    AppError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
)


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: int = Field(gt=0)
    low: int
    high: int

    @model_validator(mode="after")
    def check_range(self):
        if self.low > self.high:
            raise ValueError("low cannot be greater than high")
        return self


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/items")
    def create_item(body: Body):
        return body

    return app


def client_that_raises(error: Exception) -> TestClient:
    app = make_app()

    @app.get("/boom")
    def boom():
        raise error

    # Starlette re-raises unexpected errors after responding. Turn that off so we
    # can inspect the 500 response the way a real client would see it.
    return TestClient(app, raise_server_exceptions=False)


class FakeDriverError(Exception):
    """Stands in for the database driver's error, which carries SQLSTATE details."""

    def __init__(self, sqlstate: str) -> None:
        super().__init__("driver detail: secret_table_name")
        self.sqlstate = sqlstate
        self.diag = SimpleNamespace(constraint_name="secret_constraint_name")


class TestDomainErrors:
    @pytest.mark.parametrize(
        "error,status,code",
        [
            (NotFoundError("missing"), 404, "not_found"),
            (ConflictError("clash"), 409, "conflict"),
            (InvalidReferenceError("bad reference"), 422, "invalid_reference"),
        ],
    )
    def test_maps_to_status_and_code(self, error, status, code):
        response = client_that_raises(error).get("/boom")

        assert response.status_code == status
        assert response.json() == {"error": {"code": code, "message": error.message}}

    def test_unmapped_app_error_is_a_500_that_hides_its_message(self):
        response = client_that_raises(AppError("secret internal detail")).get("/boom")

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert "secret" not in response.text


class TestValidationErrors:
    client = TestClient(make_app(), raise_server_exceptions=False)
    valid = {"price": 10, "low": 1, "high": 5}

    def test_reports_the_failing_field(self):
        response = self.client.post("/items", json={**self.valid, "price": 0})

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["message"] == "Request validation failed"
        assert [d["field"] for d in error["details"]] == ["body.price"]

    def test_reports_every_problem_at_once(self):
        response = self.client.post("/items", json={"price": 0, "low": "x"})

        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert fields == {"body.price", "body.low", "body.high"}

    def test_cross_field_message_is_clean(self):
        response = self.client.post("/items", json={**self.valid, "low": 9})

        detail = response.json()["error"]["details"][0]
        assert detail["message"] == "low cannot be greater than high"
        assert detail["field"] == "body"

    def test_unknown_field_is_reported(self):
        response = self.client.post("/items", json={**self.valid, "is_admin": True})

        fields = [d["field"] for d in response.json()["error"]["details"]]
        assert fields == ["body.is_admin"]

    def test_details_expose_only_field_and_message(self):
        response = self.client.post("/items", json={**self.valid, "price": 0})

        for detail in response.json()["error"]["details"]:
            assert set(detail) == {"field", "message"}

    def test_malformed_json_is_a_validation_error(self):
        response = self.client.post(
            "/items", content="{not json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestHttpErrors:
    def test_unknown_route_uses_the_same_shape(self):
        response = TestClient(make_app()).get("/nope")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_wrong_method_is_405_and_keeps_the_allow_header(self):
        response = TestClient(make_app()).get("/items")

        assert response.status_code == 405
        assert response.json()["error"]["code"] == "method_not_allowed"
        assert "POST" in response.headers["allow"]

    def test_explicit_http_exception_is_reshaped(self):
        response = client_that_raises(
            HTTPException(status_code=503, detail="Database unavailable")
        ).get("/boom")

        assert response.status_code == 503
        assert response.json() == {
            "error": {"code": "service_unavailable", "message": "Database unavailable"}
        }


class TestDatabaseErrors:
    @pytest.mark.parametrize(
        "sqlstate,status,code",
        [
            ("23505", 409, "conflict"),  # unique violation
            ("23503", 409, "conflict"),  # foreign key violation
            ("23514", 422, "invalid_data"),  # check constraint
            ("23502", 422, "invalid_data"),  # not null
        ],
    )
    def test_integrity_errors_are_translated_without_leaking(self, sqlstate, status, code):
        error = IntegrityError("INSERT INTO secret_table", {}, FakeDriverError(sqlstate))

        response = client_that_raises(error).get("/boom")

        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert "secret" not in response.text

    def test_database_outage_is_a_503_without_internals(self):
        error = OperationalError("SELECT secret_query", {}, Exception("secret host"))

        response = client_that_raises(error).get("/boom")

        assert response.status_code == 503
        assert response.json()["error"]["message"] == "Database unavailable"
        assert "secret" not in response.text


class TestUnexpectedErrors:
    def test_returns_a_generic_500(self):
        response = client_that_raises(RuntimeError("secret stack detail")).get("/boom")

        assert response.status_code == 500
        assert response.json() == {
            "error": {"code": "internal_error", "message": "Internal server error"}
        }
