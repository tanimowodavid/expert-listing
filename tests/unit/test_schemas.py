import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import AgentCreate, ListingCreate, ListingSearchParams, ListingUpdate

VALID_LISTING = {
    "agent_id": str(uuid.uuid4()),
    "title": "2-bed in Lekki",
    "price": "3500000.00",
    "listing_type": "rent",
    "bedrooms": 2,
    "latitude": 6.4474,
    "longitude": 3.4745,
}


def listing(**overrides):
    return {**VALID_LISTING, **overrides}


class TestListingCreate:
    def test_accepts_valid_payload(self):
        obj = ListingCreate.model_validate(VALID_LISTING)
        assert obj.price == Decimal("3500000.00")
        assert obj.listing_type == "rent"

    def test_strips_title_whitespace(self):
        obj = ListingCreate.model_validate(listing(title="  Cozy flat  "))
        assert obj.title == "Cozy flat"

    @pytest.mark.parametrize(
        "overrides",
        [
            {"price": "9999999999.99"},  # largest value NUMERIC(12,2) holds
            {"latitude": 90, "longitude": 180},
            {"latitude": -90, "longitude": -180},
            {"bedrooms": 0},  # studios are valid
        ],
    )
    def test_accepts_boundary_values(self, overrides):
        ListingCreate.model_validate(listing(**overrides))

    @pytest.mark.parametrize(
        "overrides",
        [
            {"price": 0},
            {"price": -1},
            {"price": "10.999"},  # too many decimal places
            {"price": "10000000000"},  # too many digits for NUMERIC(12,2)
            {"listing_type": "lease"},
            {"bedrooms": -1},
            {"bedrooms": 51},
            {"latitude": 90.1},
            {"latitude": -90.1},
            {"longitude": 180.1},
            {"longitude": -180.1},
            {"title": "   "},
            {"title": "x" * 201},
            {"agent_id": "not-a-uuid"},
            {"unexpected": "field"},
        ],
    )
    def test_rejects_invalid_payload(self, overrides):
        with pytest.raises(ValidationError):
            ListingCreate.model_validate(listing(**overrides))

    @pytest.mark.parametrize("missing", list(VALID_LISTING))
    def test_rejects_missing_required_field(self, missing):
        payload = {k: v for k, v in VALID_LISTING.items() if k != missing}
        with pytest.raises(ValidationError):
            ListingCreate.model_validate(payload)


class TestListingUpdate:
    def test_partial_update_tracks_only_sent_fields(self):
        obj = ListingUpdate.model_validate({"price": "4000000"})
        assert obj.model_dump(exclude_unset=True) == {"price": Decimal("4000000")}

    def test_description_can_be_cleared(self):
        obj = ListingUpdate.model_validate({"description": None})
        assert obj.model_dump(exclude_unset=True) == {"description": None}

    def test_coordinates_can_be_updated_together(self):
        ListingUpdate.model_validate({"latitude": 6.5, "longitude": 3.4})

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"title": None},
            {"price": None},
            {"latitude": 6.5},
            {"longitude": 3.4},
            {"price": -5},
            {"agent_id": str(uuid.uuid4())},  # not updatable
        ],
    )
    def test_rejects_invalid_update(self, payload):
        with pytest.raises(ValidationError):
            ListingUpdate.model_validate(payload)


class TestListingSearchParams:
    def test_all_filters_are_optional(self):
        params = ListingSearchParams()
        assert not params.has_geo_filter

    def test_accepts_full_geo_filter(self):
        params = ListingSearchParams(latitude=6.5244, longitude=3.3792, radius_km=10)
        assert params.has_geo_filter

    def test_equal_min_and_max_are_allowed(self):
        ListingSearchParams(
            min_price=Decimal("100"),
            max_price=Decimal("100"),
            min_bedrooms=2,
            max_bedrooms=2,
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"min_price": 5, "max_price": 1},
            {"min_price": -1},
            {"min_bedrooms": 3, "max_bedrooms": 1},
            {"latitude": 6.5},
            {"latitude": 6.5, "longitude": 3.4},
            {"radius_km": 5},
            {"latitude": 6.5, "longitude": 3.4, "radius_km": 0},
            {"latitude": 6.5, "longitude": 3.4, "radius_km": 101},
            {"listing_type": "lease"},
            {"unknown_filter": 1},
        ],
    )
    def test_rejects_invalid_params(self, kwargs):
        with pytest.raises(ValidationError):
            ListingSearchParams(**kwargs)


class TestAgentCreate:
    VALID = {"name": "Ada", "email": "ada@example.com", "phone": "08012345678"}

    def test_normalises_input(self):
        agent = AgentCreate(name=" Ada ", email="Ada@Example.COM", phone="0801 234-5678")
        assert agent.name == "Ada"
        assert agent.email == "ada@example.com"
        assert agent.phone == "08012345678"

    def test_accepts_international_format(self):
        agent = AgentCreate(**{**self.VALID, "phone": "+234 801 234 5678"})
        assert agent.phone == "+2348012345678"

    @pytest.mark.parametrize(
        "field,value",
        [
            ("email", "not-an-email"),
            ("phone", "abc"),
            ("phone", "123"),
            ("name", ""),
            ("name", "x" * 101),
        ],
    )
    def test_rejects_invalid(self, field, value):
        with pytest.raises(ValidationError):
            AgentCreate(**{**self.VALID, field: value})