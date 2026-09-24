import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidReferenceError, NotFoundError
from app.models import Listing
from app.repositories import AgentRepository, ListingRepository
from app.schemas import (
    ListingCreate,
    ListingSearchParams,
    ListingSearchResult,
    ListingUpdate,
)


class ListingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.listings = ListingRepository(db)
        self.agents = AgentRepository(db)

    def create(self, data: ListingCreate) -> Listing:
        if self.agents.get(data.agent_id) is None:
            raise InvalidReferenceError(f"Agent {data.agent_id} does not exist")

        listing = self.listings.create(data)
        self.db.commit()
        return listing

    def get(self, listing_id: uuid.UUID) -> Listing:
        listing = self.listings.get(listing_id)
        if listing is None:
            raise NotFoundError("Listing not found")
        return listing

    def update(self, listing_id: uuid.UUID, data: ListingUpdate) -> Listing:
        listing = self.get(listing_id)
        # exclude_unset keeps only what the client actually sent (see step 5)
        self.listings.update(listing, data.model_dump(exclude_unset=True))
        self.db.commit()
        return listing

    def delete(self, listing_id: uuid.UUID) -> None:
        listing = self.get(listing_id)
        self.listings.soft_delete(listing)
        self.db.commit()

    def search(
        self, params: ListingSearchParams, *, limit: int, offset: int
    ) -> tuple[list[ListingSearchResult], int]:
        hits, total = self.listings.search(params, limit=limit, offset=offset)
        results = [
            ListingSearchResult.model_validate(listing).model_copy(
                update={"distance_km": None if distance is None else round(distance, 3)}
            )
            for listing, distance in hits
        ]
        return results, total
