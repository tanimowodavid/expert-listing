from fastapi import FastAPI

from app.api import agent, health, listing
from app.api.errors import register_exception_handlers
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(agent.router)
app.include_router(listing.router)