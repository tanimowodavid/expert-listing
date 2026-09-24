import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Agent
from app.repositories import AgentRepository
from app.schemas import AgentCreate


class AgentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.agents = AgentRepository(db)

    def create(self, data: AgentCreate) -> Agent:
        # Friendly fast path: check first so the common case never hits the database error.
        if self.agents.get_by_email(data.email) is not None:
            raise ConflictError("An agent with this email already exists")

        try:
            agent = self.agents.create(data)
            self.db.commit()
        except IntegrityError as exc:
            # Two requests can pass the check above at the same time. The UNIQUE
            # constraint is the real guarantee, so we translate its failure too.
            self.db.rollback()
            raise ConflictError("An agent with this email already exists") from exc
        return agent

    def get(self, agent_id: uuid.UUID) -> Agent:
        agent = self.agents.get(agent_id)
        if agent is None:
            raise NotFoundError("Agent not found")
        return agent