import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    """Same server and credentials as the dev database, but a *_test database."""
    url = make_url(Settings().database_url)
    name = url.database or "listings_db"
    if not name.endswith("_test"):
        name += "_test"
    return url.set(database=name).render_as_string(hide_password=False)


# Must happen BEFORE the app is imported: it makes get_settings(), the engine and
# Alembic's env.py all point at the test database for the whole test run.
os.environ["DATABASE_URL"] = _test_database_url()

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def test_database() -> Generator[None, None, None]:
    """Create a fresh, fully migrated test database once per test run."""
    url = make_url(os.environ["DATABASE_URL"])
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    name = admin.dialect.identifier_preparer.quote(url.database or "listings_db_test")
    try:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {name}"))
    except OperationalError:
        pytest.skip("Database server not reachable. Start it with: docker compose up -d db")
    finally:
        admin.dispose()

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")

    yield
    engine.dispose()


@pytest.fixture
def db_session(test_database) -> Generator[Session, None, None]:
    """A session whose work is rolled back when the test ends."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()