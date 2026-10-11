import os
from urllib.parse import urlparse

# 1. Check TEST_DATABASE_URL and enforce kharcha_test before ANY app import
test_db_url = os.environ.get("TEST_DATABASE_URL")
if not test_db_url:
    raise RuntimeError("TEST_DATABASE_URL environment variable is missing")

parsed = urlparse(test_db_url.replace("+psycopg", "").replace("+asyncpg", ""))
db_name = parsed.path.lstrip("/")
if db_name != "kharcha_test":
    raise RuntimeError(f"TEST_DATABASE_URL must point to 'kharcha_test', but points to '{db_name}'")

# Force DATABASE_URL to TEST_DATABASE_URL for all tests and application sessions during pytest
os.environ["DATABASE_URL"] = test_db_url

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.settings import settings  # noqa: E402
from app.db import session as db_session  # noqa: E402

# Update runtime settings and recreate the global engine and session maker if needed
settings.DATABASE_URL = test_db_url
db_session.engine = create_async_engine(test_db_url, echo=False)
db_session.AsyncSessionLocal.configure(bind=db_session.engine)


# Force test queue prefix and test Redis database/url for RQ in tests
os.environ["QUEUE_PREFIX"] = "test-"
settings.QUEUE_PREFIX = "test-"

# If REDIS_URL has /0 or unspecified, ensure tests use /1 if available, or test- queue prefix
if settings.REDIS_URL.endswith("/0"):
    settings.REDIS_URL = settings.REDIS_URL[:-2] + "/1"
    os.environ["REDIS_URL"] = settings.REDIS_URL


@pytest.fixture(scope="session", autouse=True)
def guard_test_database():
    """Verify before running any test that the active engine points strictly to kharcha_test
    and queues use test prefix."""
    current_db = db_session.engine.url.database
    if current_db != "kharcha_test":
        raise RuntimeError(
            f"CRITICAL: Active database is '{current_db}'! Tests must only run against 'kharcha_test'."
        )
    if not settings.QUEUE_PREFIX.startswith("test-"):
        raise RuntimeError(
            f"CRITICAL: Active QUEUE_PREFIX is '{settings.QUEUE_PREFIX}'! Tests must use 'test-' prefix."
        )
    yield
