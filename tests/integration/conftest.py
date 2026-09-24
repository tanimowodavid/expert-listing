from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import ListingType
from app.repositories import AgentRepository, ListingRepository
from app.schemas import AgentCreate, ListingCreate


@pytest.fixture
def agent(db_session):
    return AgentRepository(db_session).create(
        AgentCreate(name="Ada Obi", email="ada@example.com", phone="08012345678")
    )


@pytest.fixture
def listing_repo(db_session):
    return ListingRepository(db_session)


@pytest.fixture
def make_listing(listing_repo, agent):
    """Factory: creates a listing with sensible defaults, override what matters."""

    def _make(**overrides):
        data = {
            "agent_id": agent.id,
            "title": "2-bed flat",
            "price": Decimal("1500000.00"),
            "listing_type": ListingType.RENT,
            "bedrooms": 2,
            "latitude": 6.5244,
            "longitude": 3.3792,
        }
        data.update(overrides)
        return listing_repo.create(ListingCreate(**data))

    return _make


@pytest.fixture
def api(db_session):
    """A test client whose requests all run inside the test's rolled-back transaction."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
