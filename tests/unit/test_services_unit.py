import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, InvalidReferenceError, NotFoundError
from app.repositories import AgentRepository, ListingRepository
from app.schemas import AgentCreate, ListingCreate, ListingUpdate
from app.services import AgentService, ListingService


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def listing_service(db):
    service = ListingService(db)
    service.listings = MagicMock(spec=ListingRepository)
    service.agents = MagicMock(spec=AgentRepository)
    return service


@pytest.fixture
def agent_service(db):
    service = AgentService(db)
    service.agents = MagicMock(spec=AgentRepository)
    return service


def listing_data():
    return ListingCreate(
        agent_id=uuid.uuid4(),
        title="2-bed",
        price=Decimal("1000000"),
        listing_type="rent",
        bedrooms=2,
        latitude=6.5,
        longitude=3.4,
    )


class TestListingCreate:
    def test_commits_once_when_agent_exists(self, listing_service, db):
        listing_service.agents.get.return_value = object()

        result = listing_service.create(listing_data())

        assert result is listing_service.listings.create.return_value
        db.commit.assert_called_once()

    def test_unknown_agent_is_rejected_without_writing(self, listing_service, db):
        listing_service.agents.get.return_value = None

        with pytest.raises(InvalidReferenceError):
            listing_service.create(listing_data())

        listing_service.listings.create.assert_not_called()
        db.commit.assert_not_called()


class TestListingGet:
    def test_missing_listing_raises_not_found(self, listing_service):
        listing_service.listings.get.return_value = None

        with pytest.raises(NotFoundError):
            listing_service.get(uuid.uuid4())


class TestListingUpdate:
    def test_passes_only_the_sent_fields(self, listing_service, db):
        listing = listing_service.listings.get.return_value

        listing_service.update(uuid.uuid4(), ListingUpdate(price="4000000"))

        listing_service.listings.update.assert_called_once_with(
            listing, {"price": Decimal("4000000")}
        )
        db.commit.assert_called_once()

    def test_missing_listing_is_not_found_and_nothing_is_saved(
        self, listing_service, db
    ):
        listing_service.listings.get.return_value = None

        with pytest.raises(NotFoundError):
            listing_service.update(uuid.uuid4(), ListingUpdate(price="4000000"))

        listing_service.listings.update.assert_not_called()
        db.commit.assert_not_called()


class TestListingDelete:
    def test_soft_deletes_and_commits(self, listing_service, db):
        listing = listing_service.listings.get.return_value

        listing_service.delete(uuid.uuid4())

        listing_service.listings.soft_delete.assert_called_once_with(listing)
        db.commit.assert_called_once()

    def test_missing_listing_is_not_found_and_nothing_is_saved(
        self, listing_service, db
    ):
        listing_service.listings.get.return_value = None

        with pytest.raises(NotFoundError):
            listing_service.delete(uuid.uuid4())

        listing_service.listings.soft_delete.assert_not_called()
        db.commit.assert_not_called()


class TestAgentCreate:
    DATA = AgentCreate(name="Ada", email="ada@example.com", phone="08012345678")

    def test_duplicate_email_is_a_conflict(self, agent_service, db):
        agent_service.agents.get_by_email.return_value = object()

        with pytest.raises(ConflictError):
            agent_service.create(self.DATA)

        agent_service.agents.create.assert_not_called()
        db.commit.assert_not_called()

    def test_race_on_unique_constraint_becomes_a_conflict_and_rolls_back(
        self, agent_service, db
    ):
        # The pre-check passes, but the database still rejects the insert
        agent_service.agents.get_by_email.return_value = None
        agent_service.agents.create.side_effect = IntegrityError("INSERT", {}, Exception())

        with pytest.raises(ConflictError):
            agent_service.create(self.DATA)

        db.rollback.assert_called_once()
        db.commit.assert_not_called()

    def test_commits_once_on_success(self, agent_service, db):
        agent_service.agents.get_by_email.return_value = None

        agent_service.create(self.DATA)

        db.commit.assert_called_once()


class TestAgentGet:
    def test_missing_agent_raises_not_found(self, agent_service):
        agent_service.agents.get.return_value = None

        with pytest.raises(NotFoundError):
            agent_service.get(uuid.uuid4())