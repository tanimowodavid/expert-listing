import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import engine

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_database")]


def test_readiness_against_real_database(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_postgis_extension_is_enabled():
    with engine.connect() as connection:
        version = connection.execute(text("SELECT PostGIS_Version()")).scalar()

    assert version


def test_migration_created_expected_tables():
    tables = set(inspect(engine).get_table_names())

    assert {"agents", "listings", "alembic_version"} <= tables