import uuid

import pytest

from app.models import ListingType
from app.seed import AGENTS, LISTINGS, build_listings


@pytest.fixture
def listings():
    return build_listings({key: uuid.uuid4() for key in AGENTS})


def test_every_row_builds_a_valid_listing(listings):
    # Building ListingCreate objects runs the real validation rules on every row
    assert len(listings) == len(LISTINGS)


def test_titles_are_unique_per_agent(listings):
    keys = [(item.agent_id, item.title) for item in listings]
    assert len(keys) == len(set(keys))


def test_every_type_is_represented(listings):
    assert {item.listing_type for item in listings} == set(ListingType)


def test_every_agent_has_listings(listings):
    assert len({item.agent_id for item in listings}) == len(AGENTS)


def test_coordinates_stay_inside_lagos(listings):
    for item in listings:
        assert 6.3 <= item.latitude <= 6.8
        assert 3.1 <= item.longitude <= 3.7


def test_no_two_listings_share_a_location(listings):
    points = [(item.latitude, item.longitude) for item in listings]
    assert len(points) == len(set(points))
