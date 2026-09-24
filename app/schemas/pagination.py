from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_OFFSET = 10_000


class PaginationParams(BaseModel):
    """Query-string parameters shared by every list endpoint."""

    model_config = ConfigDict(extra="forbid")

    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="Page size (max 100)")] = (
        DEFAULT_LIMIT
    )
    offset: Annotated[int, Field(ge=0, le=MAX_OFFSET, description="Number of results to skip")] = 0


class Page[T](BaseModel):
    """The response envelope for any paginated endpoint."""

    items: list[T]
    total: int = Field(description="Number of matching results across all pages")
    limit: int
    offset: int
