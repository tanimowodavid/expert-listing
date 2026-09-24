from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import AgentService, ListingService

DbSession = Annotated[Session, Depends(get_db)]


def get_agent_service(db: DbSession) -> AgentService:
    return AgentService(db)


def get_listing_service(db: DbSession) -> ListingService:
    return ListingService(db)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
ListingServiceDep = Annotated[ListingService, Depends(get_listing_service)]