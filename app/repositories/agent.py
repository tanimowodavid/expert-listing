import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent
from app.schemas import AgentCreate


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: AgentCreate) -> Agent:
        agent = Agent(name=data.name, email=data.email, phone=data.phone)
        self.db.add(agent)
        self.db.flush()
        self.db.refresh(agent)  # load server-generated values (created_at)
        return agent

    def get(self, agent_id: uuid.UUID) -> Agent | None:
        return self.db.get(Agent, agent_id)

    def get_by_email(self, email: str) -> Agent | None:
        return self.db.scalar(select(Agent).where(Agent.email == email.lower()))