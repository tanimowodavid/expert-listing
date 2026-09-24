import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agent import Agent


class ListingType(enum.StrEnum):
    RENT = "rent"
    SALE = "sale"
    SHORTLET = "shortlet"


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_listings_price_positive"),
        CheckConstraint("bedrooms >= 0", name="ck_listings_bedrooms_non_negative"),
        Index("ix_listings_agent_id", "agent_id"),
        Index("ix_listings_bedrooms", "bedrooms"),
        Index("ix_listings_type_price", "listing_type", "price"),
        Index("ix_listings_location", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    listing_type: Mapped[ListingType] = mapped_column(
        Enum(
            ListingType,
            name="listing_type",
            values_callable=lambda e: [member.value for member in e],
        )
    )
    bedrooms: Mapped[int]
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="listings")