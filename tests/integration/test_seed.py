import pytest

from app.repositories import ListingRepository
from app.schemas import ListingSearchParams
from app.seed import AGENTS, LISTINGS, seed

pytestmark = pytest.mark.integration


def total_listings(db) -> int:
    _, total = ListingRepository(db).search(ListingSearchParams(), limit=1, offset=0)
    return total


def test_seed_creates_everything(db_session):
    result = seed(db_session)

    assert result.agents_created == len(AGENTS)
    assert result.listings_created == len(LISTINGS)
    assert result.listings_skipped == 0
    assert total_listings(db_session) == len(LISTINGS)


def test_seed_is_idempotent(db_session):
    seed(db_session)

    second = seed(db_session)

    assert second.agents_created == 0
    assert second.listings_created == 0
    assert second.listings_skipped == len(LISTINGS)
    assert total_listings(db_session) == len(LISTINGS)


def test_seeded_data_supports_radius_search(db_session):
    seed(db_session)

    # 5 km around Lekki Phase 1
    hits, total = ListingRepository(db_session).search(
        ListingSearchParams(latitude=6.4478, longitude=3.4723, radius_km=5),
        limit=50,
        offset=0,
    )

    titles = [listing.title for listing, _ in hits]
    distances = [distance for _, distance in hits]
    assert total >= 3
    assert "Lekki" in titles[0]  # nearest first
    assert distances == sorted(distances)
    assert not any(area in title for title in titles for area in ("Ikeja", "Ikorodu", "Yaba"))
