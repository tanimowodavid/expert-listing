import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def payload(agent):
    return {
        "agent_id": str(agent.id),
        "title": "2-bed in Lekki",
        "description": "Sea view",
        "price": "3500000",
        "listing_type": "rent",
        "bedrooms": 2,
        "latitude": 6.4474,
        "longitude": 3.4745,
    }


@pytest.fixture
def created(api, payload):
    return api.post("/listings", json=payload).json()


class TestCreate:
    def test_returns_201_with_location_and_public_fields_only(self, api, payload):
        response = api.post("/listings", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert response.headers["location"] == f"/listings/{body['id']}"
        assert body["price"] == "3500000.00"
        assert body["latitude"] == pytest.approx(6.4474)
        assert body["longitude"] == pytest.approx(3.4745)
        assert body["listing_type"] == "rent"
        assert "is_active" not in body
        assert "location" not in body

    def test_created_listing_can_be_fetched(self, api, created):
        response = api.get(f"/listings/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    def test_unknown_agent_returns_422(self, api, payload):
        response = api.post("/listings", json={**payload, "agent_id": str(uuid.uuid4())})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_reference"
        assert "does not exist" in response.json()["error"]["message"]

    @pytest.mark.parametrize(
        "overrides",
        [
            {"price": 0},
            {"price": "10.999"},
            {"latitude": 91},
            {"longitude": -181},
            {"listing_type": "lease"},
            {"bedrooms": -1},
            {"title": ""},
            {"is_active": False},  # mass assignment attempt
            {"id": str(uuid.uuid4())},  # clients cannot choose ids
        ],
    )
    def test_invalid_payload_returns_422(self, api, payload, overrides):
        response = api.post("/listings", json={**payload, **overrides})

        assert response.status_code == 422

    def test_missing_field_returns_422(self, api, payload):
        del payload["price"]

        assert api.post("/listings", json=payload).status_code == 422


class TestGet:
    def test_unknown_listing_returns_404(self, api):
        assert api.get(f"/listings/{uuid.uuid4()}").status_code == 404

    def test_malformed_id_returns_422(self, api):
        assert api.get("/listings/not-a-uuid").status_code == 422


class TestPatch:
    def test_updates_only_the_sent_fields(self, api, created):
        response = api.patch(f"/listings/{created['id']}", json={"price": "4000000"})

        assert response.status_code == 200
        body = response.json()
        assert body["price"] == "4000000.00"
        assert body["title"] == created["title"]
        assert body["bedrooms"] == created["bedrooms"]

    def test_moves_the_listing(self, api, created):
        response = api.patch(
            f"/listings/{created['id']}",
            json={"latitude": 6.6018, "longitude": 3.3515},
        )

        assert response.json()["latitude"] == pytest.approx(6.6018)
        assert response.json()["longitude"] == pytest.approx(3.3515)

    def test_description_can_be_cleared(self, api, created):
        response = api.patch(f"/listings/{created['id']}", json={"description": None})

        assert response.status_code == 200
        assert response.json()["description"] is None

    @pytest.mark.parametrize(
        "body",
        [
            {},  # nothing to update
            {"title": None},  # required fields cannot be nulled
            {"latitude": 6.5},  # coordinates come as a pair
            {"price": -5},
            {"agent_id": str(uuid.uuid4())},  # cannot be reassigned
            {"is_active": True},
        ],
    )
    def test_invalid_update_returns_422(self, api, created, body):
        response = api.patch(f"/listings/{created['id']}", json=body)

        assert response.status_code == 422

    def test_unknown_listing_returns_404(self, api):
        response = api.patch(f"/listings/{uuid.uuid4()}", json={"price": "1"})

        assert response.status_code == 404


class TestDelete:
    def test_returns_204_and_listing_disappears(self, api, created):
        response = api.delete(f"/listings/{created['id']}")

        assert response.status_code == 204
        assert response.content == b""
        assert api.get(f"/listings/{created['id']}").status_code == 404

    def test_deleting_again_returns_404(self, api, created):
        api.delete(f"/listings/{created['id']}")

        assert api.delete(f"/listings/{created['id']}").status_code == 404

    def test_cannot_update_a_deleted_listing(self, api, created):
        api.delete(f"/listings/{created['id']}")

        response = api.patch(f"/listings/{created['id']}", json={"price": "1"})

        assert response.status_code == 404

    def test_unknown_listing_returns_404(self, api):
        assert api.delete(f"/listings/{uuid.uuid4()}").status_code == 404
