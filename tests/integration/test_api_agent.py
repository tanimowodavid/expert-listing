import uuid

import pytest

pytestmark = pytest.mark.integration

PAYLOAD = {"name": "Tunde", "email": "Tunde@Example.com", "phone": "0801 111 2222"}


def test_create_returns_201_with_normalised_data_and_location(api):
    response = api.post("/agents", json=PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "tunde@example.com"
    assert body["phone"] == "08011112222"
    assert response.headers["location"] == f"/agents/{body['id']}"


def test_created_agent_can_be_fetched(api):
    agent_id = api.post("/agents", json=PAYLOAD).json()["id"]

    response = api.get(f"/agents/{agent_id}")

    assert response.status_code == 200
    assert response.json()["id"] == agent_id


def test_duplicate_email_returns_409(api):
    api.post("/agents", json=PAYLOAD)

    response = api.post("/agents", json={**PAYLOAD, "email": "tunde@example.com"})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "not-an-email"},
        {"phone": "abc"},
        {"name": ""},
        {"is_admin": True},  # unknown fields are rejected
    ],
)
def test_invalid_payload_returns_422(api, overrides):
    response = api.post("/agents", json={**PAYLOAD, **overrides})

    assert response.status_code == 422


def test_unknown_agent_returns_404(api):
    assert api.get(f"/agents/{uuid.uuid4()}").status_code == 404


def test_malformed_id_returns_422(api):
    assert api.get("/agents/not-a-uuid").status_code == 422