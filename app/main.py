from fastapi import FastAPI

from app.api import agent, health, listing
from app.api.errors import register_exception_handlers
from app.core.config import get_settings
from app.schemas.error import ErrorResponse

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(agent.router)
app.include_router(listing.router)

