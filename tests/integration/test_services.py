import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError, InvalidReferenceError, NotFoundError
from app.schemas import (
    AgentCreate,
    ListingCreate,
    ListingSearchParams,
    ListingSearchResult,
    ListingUpdate,
)
from app.services import AgentService, ListingService

pytestmark = pytest.mark.integration

LEKKI = {"latitude": 6.4474, "longitude": 3.4745}
IKEJA = {"latitude": 6.6018, "longitude": 3.3515}


@pytest.fixture
def listing_service(db_session):
    return ListingService(db_session)


@pytest.fixture
def agent_service(db_session):
    return AgentService(db_session)


def new_listing(agent_id, **overrides):
    data = {
        "agent_id": agent_id,
        "title": "2-bed flat",
        "price": Decimal("1500000"),
        "listing_type": "rent",
        "bedrooms": 2,
        **LEKKI,
    }
    data.update(overrides)
    return ListingCreate(**data)


class TestAgents:
    def test_create_and_get(self, agent_service):
        created = agent_service.create(
            AgentCreate(name="Tunde", email="Tunde@Example.com", phone="08011112222")
        )

        assert agent_service.get(created.id).email == "tunde@example.com"

    def test_duplicate_email_is_a_conflict(self, agent_service, agent):
        with pytest.raises(ConflictError):
            agent_service.create(
                AgentCreate(name="Other", email="ADA@example.com", phone="08099999999")
            )

    def test_unknown_agent_is_not_found(self, agent_service):
        with pytest.raises(NotFoundError):
            agent_service.get(uuid.uuid4())


class TestListingCreate:
    def test_creates_a_listing_for_an_existing_agent(self, listing_service, agent):
        listing = listing_service.create(new_listing(agent.id))

        assert listing_service.get(listing.id).title == "2-bed flat"

    def test_unknown_agent_is_an_invalid_reference(self, listing_service):
        with pytest.raises(InvalidReferenceError):
            listing_service.create(new_listing(uuid.uuid4()))


class TestListingUpdate:
    def test_partial_update_leaves_other_fields_alone(self, listing_service, agent):
        listing = listing_service.create(new_listing(agent.id, title="Old title"))

        updated = listing_service.update(listing.id, ListingUpdate(price="2500000"))

        assert updated.price == Decimal("2500000.00")
        assert updated.title == "Old title"

    def test_moves_the_listing(self, listing_service, agent):
        listing = listing_service.create(new_listing(agent.id))

        updated = listing_service.update(listing.id, ListingUpdate(**IKEJA))

        assert updated.latitude == pytest.approx(IKEJA["latitude"])
        assert updated.longitude == pytest.approx(IKEJA["longitude"])

    def test_unknown_listing_is_not_found(self, listing_service):
        with pytest.raises(NotFoundError):
            listing_service.update(uuid.uuid4(), ListingUpdate(price="1"))


class TestListingDelete:
    def test_deleted_listing_is_gone(self, listing_service, agent):
        listing = listing_service.create(new_listing(agent.id))

        listing_service.delete(listing.id)

        with pytest.raises(NotFoundError):
            listing_service.get(listing.id)

    def test_deleting_twice_is_not_found(self, listing_service, agent):
        listing = listing_service.create(new_listing(agent.id))
        listing_service.delete(listing.id)

        with pytest.raises(NotFoundError):
            listing_service.delete(listing.id)

    def test_deleted_listing_disappears_from_search(self, listing_service, agent):
        keep = listing_service.create(new_listing(agent.id, title="Keep"))
        gone = listing_service.create(new_listing(agent.id, title="Gone"))
        listing_service.delete(gone.id)

        results, total = listing_service.search(ListingSearchParams(), limit=10, offset=0)

        assert [r.id for r in results] == [keep.id]
        assert total == 1


class TestListingSearch:
    def test_results_are_search_models_with_rounded_distance(self, listing_service, agent):
        listing_service.create(new_listing(agent.id, **LEKKI))
        listing_service.create(new_listing(agent.id, **IKEJA))

        results, total = listing_service.search(
            ListingSearchParams(radius_km=50, **LEKKI), limit=10, offset=0
        )

        assert total == 2
        assert all(isinstance(r, ListingSearchResult) for r in results)
        assert results[0].distance_km == pytest.approx(0, abs=0.01)  # nearest first
        assert results[1].distance_km > results[0].distance_km
        assert results[1].distance_km == round(results[1].distance_km, 3)

    def test_distance_is_none_without_a_location_filter(self, listing_service, agent):
        listing_service.create(new_listing(agent.id))

        results, _ = listing_service.search(ListingSearchParams(), limit=10, offset=0)

        assert results[0].distance_km is None
