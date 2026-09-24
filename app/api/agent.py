import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import AgentServiceDep
from app.schemas import AgentCreate, AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent",
    responses={409: {"description": "An agent with this email already exists"}},
)
def create_agent(
    data: AgentCreate,
    request: Request,
    response: Response,
    service: AgentServiceDep,
):
    agent = service.create(data)
    response.headers["Location"] = str(
        request.app.url_path_for("get_agent", agent_id=str(agent.id))
    )
    return agent


@router.get(
    "/{agent_id}",
    response_model=AgentRead,
    summary="Get an agent",
    responses={404: {"description": "Agent not found"}},
)
def get_agent(agent_id: uuid.UUID, service: AgentServiceDep):
    return service.get(agent_id)
