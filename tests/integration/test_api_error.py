import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.repositories import AgentRepository
from app.schemas import AgentCreate

pytestmark = pytest.mark.integration


def test_invalid_listing_reports_every_bad_field(api, agent):
    response = api.post(
        "/listings",
        json={
            "agent_id": str(agent.id),
            "title": "Flat",
            "price": 0,
            "listing_type": "lease",
            "bedrooms": 1,
            "latitude": 95,
            "longitude": 3.4,
        },
    )

    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"body.price", "body.listing_type", "body.latitude"}


def test_empty_patch_explains_itself(api, agent):
    listing_id = api.post(
        "/listings",
        json={
            "agent_id": str(agent.id),
            "title": "Flat",
            "price": "1000",
            "listing_type": "rent",
            "bedrooms": 1,
            "latitude": 6.5,
            "longitude": 3.4,
        },
    ).json()["id"]

    response = api.patch(f"/listings/{listing_id}", json={})

    assert response.status_code == 422
    assert "at least one field" in response.json()["error"]["details"][0]["message"]


def test_malformed_path_id_names_the_path_parameter(api):
    response = api.get("/listings/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "path.listing_id"


def test_missing_listing_uses_the_error_envelope(api):
    response = api.get(f"/listings/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Listing not found"}}


def test_stray_unique_violation_becomes_a_clean_409(db_session, agent):
    """Skip the service's pre-check and let PostgreSQL itself reject the insert."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/duplicate-agent")
    def duplicate_agent():
        AgentRepository(db_session).create(
            AgentCreate(name="Copy", email="ada@example.com", phone="08000000000")
        )

    response = TestClient(app, raise_server_exceptions=False).post("/duplicate-agent")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert "ada@example.com" not in response.text
    assert "agents" not in response.text  # no table or constraint names
