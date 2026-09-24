import uuid
from typing import Any, cast

from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy import func, null, select
from sqlalchemy.orm import Session

from app.models import Listing
from app.schemas import ListingCreate, ListingSearchParams

# Only these can change through update(). Never id, agent_id, is_active or timestamps.
UPDATABLE_FIELDS = {"title", "description", "price", "listing_type", "bedrooms"}

# A listing plus its distance from the search point in km (None without a geo filter)
SearchHit = tuple[Listing, float | None]


def _point(latitude: float, longitude: float) -> WKTElement:
    # WKT/PostGIS order is (X Y) = (longitude latitude).
    return WKTElement(f"POINT({longitude:.7f} {latitude:.7f})", srid=4326)


class ListingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ListingCreate) -> Listing:
        listing = Listing(
            agent_id=data.agent_id,
            title=data.title,
            description=data.description,
            price=data.price,
            listing_type=data.listing_type,
            bedrooms=data.bedrooms,
            location=_point(data.latitude, data.longitude),
        )
        self.db.add(listing)
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def get(self, listing_id: uuid.UUID) -> Listing | None:
        """Active listings only. Soft-deleted ones behave as if they don't exist."""
        return self.db.scalar(
            select(Listing).where(Listing.id == listing_id, Listing.is_active.is_(True))
        )

    def update(self, listing: Listing, changes: dict[str, Any]) -> Listing:
        values = dict(changes)
        latitude = values.pop("latitude", None)
        longitude = values.pop("longitude", None)

        unknown = values.keys() - UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Fields cannot be updated: {sorted(unknown)}")
        if (latitude is None) != (longitude is None):
            raise ValueError("latitude and longitude must be updated together")

        for field, value in values.items():
            setattr(listing, field, value)
        if latitude is not None and longitude is not None:
            listing.location = cast(WKBElement, _point(latitude, longitude))

        self.db.flush()
        self.db.refresh(listing)
        return listing

    def soft_delete(self, listing: Listing) -> None:
        if listing.is_active:
            listing.is_active = False
            self.db.flush()

    def search(
        self, params: ListingSearchParams, *, limit: int, offset: int
    ) -> tuple[list[SearchHit], int]:
        conditions = [Listing.is_active.is_(True)]
        if params.listing_type is not None:
            conditions.append(Listing.listing_type == params.listing_type)
        if params.min_price is not None:
            conditions.append(Listing.price >= params.min_price)
        if params.max_price is not None:
            conditions.append(Listing.price <= params.max_price)
        if params.min_bedrooms is not None:
            conditions.append(Listing.bedrooms >= params.min_bedrooms)
        if params.max_bedrooms is not None:
            conditions.append(Listing.bedrooms <= params.max_bedrooms)

        distance_km = null().label("distance_km")
        order_by = [Listing.created_at.desc(), Listing.id]

        if params.has_geo_filter:
            # The schema guarantees latitude, longitude and radius_km are all set here.
            origin = func.ST_GeogFromText(
                f"SRID=4326;POINT({params.longitude:.7f} {params.latitude:.7f})"
            )
            conditions.append(
                func.ST_DWithin(Listing.location, origin, params.radius_km * 1000)
            )
            distance_km = (func.ST_Distance(Listing.location, origin) / 1000).label(
                "distance_km"
            )
            order_by = [distance_km, Listing.id]

        total = self.db.scalar(
            select(func.count()).select_from(Listing).where(*conditions)
        )
        rows = self.db.execute(
            select(Listing, distance_km)
            .where(*conditions)
            .order_by(*order_by)
            .limit(limit)
            .offset(offset)
        ).all()

        return [(listing, distance) for listing, distance in rows], total or 0