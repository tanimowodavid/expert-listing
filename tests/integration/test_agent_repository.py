import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories import AgentRepository
from app.schemas import AgentCreate

pytestmark = pytest.mark.integration


def test_create_generates_id_and_timestamp(db_session):
    agent = AgentRepository(db_session).create(
        AgentCreate(name="Tunde", email="tunde@example.com", phone="08011112222")
    )

    assert isinstance(agent.id, uuid.UUID)
    assert agent.created_at is not None


def test_get_returns_agent(db_session, agent):
    assert AgentRepository(db_session).get(agent.id).email == "ada@example.com"


def test_get_unknown_id_returns_none(db_session):
    assert AgentRepository(db_session).get(uuid.uuid4()) is None


def test_get_by_email_ignores_case(db_session, agent):
    found = AgentRepository(db_session).get_by_email("ADA@Example.com")

    assert found.id == agent.id


def test_duplicate_email_violates_unique_constraint(db_session, agent):
    with pytest.raises(IntegrityError):
        AgentRepository(db_session).create(
            AgentCreate(name="Other", email="ada@example.com", phone="08099999999")
        )