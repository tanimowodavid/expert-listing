"""create agents and listings

Revision ID: 45b8844a82a2
Revises:
Create Date: 2026-09-24 07:51:12.832445

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "45b8844a82a2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "listing_type",
            sa.Enum("rent", "sale", "shortlet", name="listing_type"),
            nullable=False,
        ),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("price > 0", name="ck_listings_price_positive"),
        sa.CheckConstraint("bedrooms >= 0", name="ck_listings_bedrooms_non_negative"),
    )

    op.create_index("ix_listings_agent_id", "listings", ["agent_id"])
    op.create_index("ix_listings_bedrooms", "listings", ["bedrooms"])
    op.create_index("ix_listings_type_price", "listings", ["listing_type", "price"])
    op.create_index("ix_listings_location", "listings", ["location"], postgresql_using="gist")


def downgrade() -> None:
    # Dropping a table also drops its indexes and constraints.
    op.drop_table("listings")
    op.drop_table("agents")
    op.execute("DROP TYPE IF EXISTS listing_type")
