import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import ListingType

# One definition per rule, reused by create, update and search.
Title = Annotated[str, Field(min_length=1, max_length=200)]
Description = Annotated[str, Field(max_length=5000)]
Price = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
PriceFilter = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Bedrooms = Annotated[int, Field(ge=0, le=50)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]


class ListingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    agent_id: uuid.UUID
    title: Title
    description: Description | None = None
    price: Price
    listing_type: ListingType
    bedrooms: Bedrooms
    latitude: Latitude
    longitude: Longitude


class ListingUpdate(BaseModel):
    """PATCH body: every field optional, but at least one must be sent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title | None = None
    description: Description | None = None
    price: Price | None = None
    listing_type: ListingType | None = None
    bedrooms: Bedrooms | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="after")
    def check_update(self) -> Self:
        sent = self.model_fields_set
        if not sent:
            raise ValueError("Provide at least one field to update")
        for name in sent - {"description"}:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be null")
        if ("latitude" in sent) != ("longitude" in sent):
            raise ValueError("latitude and longitude must be provided together")
        return self


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    description: str | None
    price: Decimal
    listing_type: ListingType
    bedrooms: int
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime


class ListingSearchResult(ListingRead):
    """A listing plus its distance from the search point (when one was given)."""

    distance_km: float | None = None


class ListingSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_type: ListingType | None = None
    min_price: PriceFilter | None = None
    max_price: PriceFilter | None = None
    min_bedrooms: Annotated[int, Field(ge=0)] | None = None
    max_bedrooms: Annotated[int, Field(ge=0)] | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    radius_km: Annotated[float, Field(gt=0, le=100)] | None = None

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot be greater than max_price")
        if (
            self.min_bedrooms is not None
            and self.max_bedrooms is not None
            and self.min_bedrooms > self.max_bedrooms
        ):
            raise ValueError("min_bedrooms cannot be greater than max_bedrooms")

        geo = (self.latitude, self.longitude, self.radius_km)
        if any(v is not None for v in geo) and any(v is None for v in geo):
            raise ValueError(
                "latitude, longitude and radius_km must be provided together"
            )
        return self

    @property
    def has_geo_filter(self) -> bool:
        return self.latitude is not None