import pytest
from pydantic import ValidationError

from app.schemas.pagination import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_OFFSET,
    Page,
    PaginationParams,
)


def test_defaults():
    params = PaginationParams()

    assert params.limit == DEFAULT_LIMIT
    assert params.offset == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 1},
        {"limit": MAX_LIMIT},
        {"offset": 0},
        {"offset": MAX_OFFSET},
    ],
)
def test_accepts_boundary_values(kwargs):
    PaginationParams(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": MAX_LIMIT + 1},
        {"limit": "abc"},
        {"offset": -1},
        {"offset": MAX_OFFSET + 1},
        {"page": 2},  # unknown parameters are rejected, not ignored
    ],
)
def test_rejects_invalid_values(kwargs):
    with pytest.raises(ValidationError):
        PaginationParams(**kwargs)


def test_query_string_values_are_coerced():
    params = PaginationParams.model_validate({"limit": "5", "offset": "10"})

    assert (params.limit, params.offset) == (5, 10)


def test_page_envelope_shape():
    page = Page[int](items=[1, 2], total=5, limit=2, offset=0)

    assert page.model_dump() == {"items": [1, 2], "total": 5, "limit": 2, "offset": 0}


def test_page_validates_the_item_type():
    with pytest.raises(ValidationError):
        Page[int](items=["not-a-number"], total=1, limit=1, offset=0)
