import pytest
from pydantic import ValidationError

from app.schemas import ListingQuery


def test_accepts_filters_and_pagination_together():
    query = ListingQuery(
        listing_type="rent",
        min_price=1000,
        latitude=6.5,
        longitude=3.4,
        radius_km=5,
        limit=10,
        offset=20,
    )

    assert query.has_geo_filter
    assert (query.limit, query.offset) == (10, 20)


def test_query_string_values_are_coerced():
    query = ListingQuery.model_validate({"limit": "5", "min_price": "1000", "min_bedrooms": "2"})

    assert query.limit == 5
    assert query.min_bedrooms == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_price": 5, "max_price": 1},  # cross-field rules are inherited
        {"latitude": 6.5},
        {"limit": 0},
        {"offset": -1},
        {"unknown": 1},
    ],
)
def test_rejects_invalid_queries(kwargs):
    with pytest.raises(ValidationError):
        ListingQuery(**kwargs)
