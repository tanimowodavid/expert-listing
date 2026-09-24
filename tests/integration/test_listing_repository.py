import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models import ListingType
from app.schemas import ListingSearchParams

pytestmark = pytest.mark.integration

LEKKI = {"latitude": 6.4474, "longitude": 3.4745}
VICTORIA_ISLAND = {"latitude": 6.4281, "longitude": 3.4219}
YABA = {"latitude": 6.5244, "longitude": 3.3792}
IKEJA = {"latitude": 6.6018, "longitude": 3.3515}


def run_search(repo, *, limit=20, offset=0, **filters):
    return repo.search(ListingSearchParams(**filters), limit=limit, offset=offset)


def ids(hits):
    return {listing.id for listing, _ in hits}


@pytest.fixture
def market(make_listing):
    """Four listings across Lagos with different types, prices and sizes."""
    return {
        "yaba": make_listing(
            title="Yaba 1-bed", price=Decimal("1000000"), bedrooms=1, **YABA
        ),
        "lekki": make_listing(
            title="Lekki 2-bed", price=Decimal("2000000"), bedrooms=2, **LEKKI
        ),
        "vi": make_listing(
            title="VI 3-bed shortlet",
            price=Decimal("3000000"),
            bedrooms=3,
            listing_type=ListingType.SHORTLET,
            **VICTORIA_ISLAND,
        ),
        "ikeja": make_listing(
            title="Ikeja 4-bed for sale",
            price=Decimal("50000000"),
            bedrooms=4,
            listing_type=ListingType.SALE,
            **IKEJA,
        ),
    }


class TestCreateAndGet:
    def test_create_sets_defaults(self, make_listing):
        listing = make_listing()

        assert isinstance(listing.id, uuid.UUID)
        assert listing.is_active is True
        assert listing.created_at is not None

    def test_coordinates_round_trip(self, make_listing):
        listing = make_listing(**LEKKI)

        assert listing.latitude == pytest.approx(6.4474)
        assert listing.longitude == pytest.approx(3.4745)

    def test_postgis_stores_longitude_as_x(self, db_session, make_listing):
        listing = make_listing(**LEKKI)

        x, y = db_session.execute(
            text(
                "SELECT ST_X(location::geometry), ST_Y(location::geometry) "
                "FROM listings WHERE id = :id"
            ),
            {"id": listing.id},
        ).one()

        assert x == pytest.approx(3.4745)  # longitude
        assert y == pytest.approx(6.4474)  # latitude

    def test_get_returns_active_listing(self, listing_repo, make_listing):
        listing = make_listing()

        assert listing_repo.get(listing.id).id == listing.id

    def test_get_unknown_id_returns_none(self, listing_repo):
        assert listing_repo.get(uuid.uuid4()) is None


class TestUpdate:
    def test_changes_only_the_given_fields(self, listing_repo, make_listing):
        listing = make_listing(title="Old title", price=Decimal("1000000"))

        listing_repo.update(listing, {"price": Decimal("2000000")})

        assert listing.price == Decimal("2000000")
        assert listing.title == "Old title"

    def test_updates_location(self, listing_repo, make_listing):
        listing = make_listing(**YABA)

        listing_repo.update(listing, IKEJA)

        assert listing.latitude == pytest.approx(IKEJA["latitude"])
        assert listing.longitude == pytest.approx(IKEJA["longitude"])

    def test_description_can_be_cleared(self, listing_repo, make_listing):
        listing = make_listing(description="Nice place")

        listing_repo.update(listing, {"description": None})

        assert listing.description is None

    @pytest.mark.parametrize("field", ["is_active", "agent_id", "id", "created_at"])
    def test_rejects_fields_that_must_not_change(
        self, listing_repo, make_listing, field
    ):
        with pytest.raises(ValueError):
            listing_repo.update(make_listing(), {field: "anything"})

    def test_rejects_half_a_coordinate(self, listing_repo, make_listing):
        with pytest.raises(ValueError):
            listing_repo.update(make_listing(), {"latitude": 6.5})


class TestSoftDelete:
    def test_row_is_kept_but_hidden(self, db_session, listing_repo, make_listing):
        listing = make_listing()

        listing_repo.soft_delete(listing)

        assert listing_repo.get(listing.id) is None
        still_there = db_session.execute(
            text("SELECT is_active FROM listings WHERE id = :id"), {"id": listing.id}
        ).scalar()
        assert still_there is False

    def test_is_idempotent(self, listing_repo, make_listing):
        listing = make_listing()

        listing_repo.soft_delete(listing)
        listing_repo.soft_delete(listing)

        assert listing_repo.get(listing.id) is None

    def test_deleted_listing_is_excluded_from_search(self, listing_repo, market):
        listing_repo.soft_delete(market["yaba"])

        hits, total = run_search(listing_repo)

        assert market["yaba"].id not in ids(hits)
        assert total == 3


class TestSearchFilters:
    def test_no_filters_returns_all_active(self, listing_repo, market):
        hits, total = run_search(listing_repo)

        assert ids(hits) == {m.id for m in market.values()}
        assert total == 4

    def test_filters_by_type(self, listing_repo, market):
        hits, _ = run_search(listing_repo, listing_type="rent")

        assert ids(hits) == {market["yaba"].id, market["lekki"].id}

    def test_price_range_is_inclusive(self, listing_repo, market):
        hits, _ = run_search(listing_repo, min_price=2000000, max_price=3000000)

        assert ids(hits) == {market["lekki"].id, market["vi"].id}

    def test_bedroom_range(self, listing_repo, market):
        at_least_3, _ = run_search(listing_repo, min_bedrooms=3)
        at_most_1, _ = run_search(listing_repo, max_bedrooms=1)

        assert ids(at_least_3) == {market["vi"].id, market["ikeja"].id}
        assert ids(at_most_1) == {market["yaba"].id}

    def test_filters_combine_with_and(self, listing_repo, market):
        hits, _ = run_search(listing_repo, listing_type="rent", min_bedrooms=2)

        assert ids(hits) == {market["lekki"].id}

    def test_distance_is_none_without_geo_filter(self, listing_repo, market):
        hits, _ = run_search(listing_repo)

        assert all(distance is None for _, distance in hits)


class TestSearchGeo:
    def test_returns_only_listings_within_radius_nearest_first(
        self, listing_repo, market
    ):
        hits, total = run_search(listing_repo, radius_km=10, **LEKKI)

        assert [listing.id for listing, _ in hits] == [
            market["lekki"].id,
            market["vi"].id,
        ]
        assert total == 2

    def test_reports_distance_in_km(self, listing_repo, market):
        hits, _ = run_search(listing_repo, radius_km=10, **LEKKI)
        distances = {listing.id: distance for listing, distance in hits}

        assert distances[market["lekki"].id] == pytest.approx(0, abs=0.01)
        assert 5.5 < distances[market["vi"].id] < 7.0

    def test_radius_boundary_is_respected(self, listing_repo, market):
        hits, _ = run_search(listing_repo, radius_km=10, **LEKKI)
        vi_distance = dict((l.id, d) for l, d in hits)[market["vi"].id]

        just_inside, _ = run_search(listing_repo, radius_km=vi_distance + 0.01, **LEKKI)
        just_outside, _ = run_search(listing_repo, radius_km=vi_distance - 0.01, **LEKKI)

        assert market["vi"].id in ids(just_inside)
        assert market["vi"].id not in ids(just_outside)

    def test_no_results_when_nothing_is_near(self, listing_repo, market):
        hits, total = run_search(listing_repo, radius_km=1, latitude=9.0, longitude=7.4)

        assert hits == []
        assert total == 0

    def test_swapped_coordinates_find_nothing(self, listing_repo, market):
        # Lekki with lat/lng the wrong way round lands in the Gulf of Guinea
        hits, _ = run_search(listing_repo, radius_km=10, latitude=3.4745, longitude=6.4474)

        assert hits == []

    def test_geo_combines_with_other_filters(self, listing_repo, market):
        hits, _ = run_search(
            listing_repo, radius_km=25, listing_type="rent", **LEKKI
        )

        assert ids(hits) == {market["lekki"].id, market["yaba"].id}


class TestPagination:
    @pytest.fixture
    def five(self, make_listing):
        return [make_listing(title=f"Flat {i}") for i in range(5)]

    def test_pages_are_disjoint_and_complete(self, listing_repo, five):
        pages = [run_search(listing_repo, limit=2, offset=o) for o in (0, 2, 4)]

        assert [len(hits) for hits, _ in pages] == [2, 2, 1]
        assert all(total == 5 for _, total in pages)
        seen = [listing.id for hits, _ in pages for listing, _ in hits]
        assert len(seen) == len(set(seen)) == 5

    def test_order_is_stable_between_calls(self, listing_repo, five):
        first, _ = run_search(listing_repo, limit=5)
        second, _ = run_search(listing_repo, limit=5)

        assert [l.id for l, _ in first] == [l.id for l, _ in second]

    def test_offset_past_the_end_returns_empty_page_with_total(
        self, listing_repo, five
    ):
        hits, total = run_search(listing_repo, limit=2, offset=10)

        assert hits == []
        assert total == 5

    def test_total_respects_filters(self, listing_repo, market):
        hits, total = run_search(listing_repo, limit=1, listing_type="rent")

        assert len(hits) == 1
        assert total == 2