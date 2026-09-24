"""Seed the database with sample Lagos agents and listings.

    uv run python -m app.seed             # add sample data (safe to re-run)
    uv run python -m app.seed --reset     # delete ALL agents and listings first

The data goes through the real services and schemas, so it is validated exactly like
API input. Coordinates are approximate neighbourhood centres, not exact addresses.
Price convention used by this data: rent is per year, shortlet is per night,
sale is the total price (all in naira).
"""

import argparse
import uuid
from collections import Counter
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Listing, ListingType
from app.repositories import AgentRepository
from app.schemas import AgentCreate, ListingCreate
from app.services import AgentService, ListingService

RENT, SALE, SHORTLET = ListingType.RENT, ListingType.SALE, ListingType.SHORTLET

AGENTS = {
    "ada": AgentCreate(name="Ada Obi", email="ada.obi@example.com", phone="08012345678"),
    "tunde": AgentCreate(
        name="Tunde Bakare", email="tunde.bakare@example.com", phone="08023456789"
    ),
    "ngozi": AgentCreate(
        name="Ngozi Eze", email="ngozi.eze@example.com", phone="+2348034567890"
    ),
}

# area -> (latitude, longitude)
AREAS = {
    "Lekki Phase 1": (6.4478, 3.4723),
    "Victoria Island": (6.4281, 3.4219),
    "Ikoyi": (6.4549, 3.4246),
    "Oniru": (6.4290, 3.4500),
    "Banana Island": (6.4500, 3.4400),
    "Ajah": (6.4698, 3.5852),
    "Yaba": (6.5095, 3.3711),
    "Surulere": (6.5010, 3.3580),
    "Gbagada": (6.5550, 3.3870),
    "Ilupeju": (6.5500, 3.3600),
    "Apapa": (6.4489, 3.3592),
    "Ikeja GRA": (6.5833, 3.3500),
    "Ikeja": (6.6018, 3.3515),
    "Maryland": (6.5667, 3.3667),
    "Magodo": (6.6200, 3.3900),
    "Ikorodu": (6.6194, 3.5105),
    "Festac": (6.4667, 3.2833),
}

# (agent, title, type, price, bedrooms, area, description)
LISTINGS = [
    ("ada", "Bright 2-bedroom apartment in Lekki Phase 1", RENT, 4_500_000, 2,
     "Lekki Phase 1", "Tiled throughout, 24/7 power backup, close to shops."),
    ("ada", "Serviced 3-bedroom flat, Lekki Phase 1", RENT, 8_000_000, 3,
     "Lekki Phase 1", None),
    ("ada", "Executive 1-bedroom apartment, Victoria Island", RENT, 6_500_000, 1,
     "Victoria Island", None),
    ("ada", "Luxury 3-bedroom shortlet, Victoria Island", SHORTLET, 150_000, 3,
     "Victoria Island", "Per night. Pool, gym and concierge."),
    ("ada", "4-bedroom terrace duplex, Ikoyi", SALE, 320_000_000, 4, "Ikoyi", None),
    ("ada", "Modern studio shortlet, Ikoyi", SHORTLET, 65_000, 0, "Ikoyi", "Per night."),
    ("ada", "Waterfront 2-bedroom apartment, Oniru", RENT, 9_500_000, 2, "Oniru", None),
    ("ada", "Spacious 3-bedroom flat, Ajah", RENT, 3_500_000, 3, "Ajah", None),
    ("ada", "Newly built 4-bedroom detached house, Ajah", SALE, 85_000_000, 4,
     "Ajah", None),
    ("ada", "5-bedroom detached mansion, Banana Island", SALE, 950_000_000, 5,
     "Banana Island", None),
    ("tunde", "Self-contained studio near the university, Yaba", RENT, 900_000, 0,
     "Yaba", None),
    ("tunde", "2-bedroom flat, Yaba", RENT, 2_200_000, 2, "Yaba", None),
    ("tunde", "3-bedroom flat, Surulere", RENT, 2_800_000, 3, "Surulere", None),
    ("tunde", "Renovated 4-bedroom bungalow, Surulere", SALE, 70_000_000, 4,
     "Surulere", None),
    ("tunde", "Cosy 1-bedroom shortlet, Gbagada", SHORTLET, 45_000, 1, "Gbagada",
     "Per night."),
    ("tunde", "2-bedroom serviced apartment, Ilupeju", RENT, 3_800_000, 2,
     "Ilupeju", None),
    ("tunde", "3-bedroom flat with harbour view, Apapa", RENT, 5_000_000, 3,
     "Apapa", None),
    ("ngozi", "4-bedroom duplex, Ikeja GRA", SALE, 180_000_000, 4, "Ikeja GRA", None),
    ("ngozi", "Modern 2-bedroom flat, Ikeja", RENT, 3_000_000, 2, "Ikeja", None),
    ("ngozi", "Shortlet near the airport, Ikeja", SHORTLET, 55_000, 1, "Ikeja",
     "Per night."),
    ("ngozi", "1-bedroom shortlet, Maryland", SHORTLET, 50_000, 1, "Maryland",
     "Per night."),
    ("ngozi", "5-bedroom detached house, Magodo", SALE, 210_000_000, 5, "Magodo", None),
    ("ngozi", "Affordable 2-bedroom flat, Ikorodu", RENT, 1_200_000, 2, "Ikorodu", None),
    ("ngozi", "3-bedroom flat, Festac Town", RENT, 2_000_000, 3, "Festac", None),
]


class SeedResult(NamedTuple):
    agents_created: int
    listings_created: int
    listings_skipped: int


def build_listings(agent_ids: dict[str, uuid.UUID]) -> list[ListingCreate]:
    """Turn the table above into validated payloads (pure: no database access)."""
    seen_in_area: Counter[str] = Counter()
    payloads = []
    for agent_key, title, kind, price, bedrooms, area, description in LISTINGS:
        # Listings in the same area get a small deterministic offset (~100 m) so the
        # map isn't a stack of identical points, and re-runs produce identical data.
        n = seen_in_area[area]
        seen_in_area[area] += 1
        latitude, longitude = AREAS[area]
        payloads.append(
            ListingCreate(
                agent_id=agent_ids[agent_key],
                title=title,
                description=description,
                price=Decimal(price),
                listing_type=kind,
                bedrooms=bedrooms,
                latitude=round(latitude + n * 0.0012, 6),
                longitude=round(longitude - n * 0.0009, 6),
            )
        )
    return payloads


def seed(db: Session) -> SeedResult:
    agents = AgentRepository(db)
    agent_service = AgentService(db)
    listing_service = ListingService(db)

    agent_ids: dict[str, uuid.UUID] = {}
    agents_created = 0
    for key, data in AGENTS.items():
        agent = agents.get_by_email(data.email)
        if agent is None:
            agent = agent_service.create(data)
            agents_created += 1
        agent_ids[key] = agent.id

    created = skipped = 0
    for data in build_listings(agent_ids):
        already_there = db.scalar(
            select(Listing.id).where(
                Listing.agent_id == data.agent_id, Listing.title == data.title
            )
        )
        if already_there is not None:
            skipped += 1
            continue
        listing_service.create(data)
        created += 1

    return SeedResult(agents_created, created, skipped)


def reset(db: Session) -> None:
    db.execute(text("TRUNCATE TABLE listings, agents"))
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with sample data.")
    parser.add_argument(
        "--reset", action="store_true", help="delete ALL agents and listings first"
    )
    parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt for --reset"
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            if not args.yes:
                answer = input("This deletes ALL agents and listings. Type 'yes': ")
                if answer != "yes":
                    raise SystemExit("Aborted.")
            reset(db)
        result = seed(db)

    print(
        f"Agents created: {result.agents_created} | "
        f"listings created: {result.listings_created} | "
        f"listings already present: {result.listings_skipped}"
    )


if __name__ == "__main__":
    main()