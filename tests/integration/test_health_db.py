import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def require_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip("Database not reachable. Start it with: docker compose up -d db")


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