"""Test that Alembic migration produces schema matching schema.sql exactly."""

import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

# Add scripts directory to sys.path so we can import schema parsing and comparison logic
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.schema_diff import diff_schemas, inspect_db, parse_schema_sql  # noqa: E402


def test_migration_matches_schema():
    """Test that running migration on a clean database produces expected schema from docs/schema.sql."""
    test_db_url = os.environ["TEST_DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(test_db_url)

    # Start from an empty schema: drops tables, enum types and alembic_version
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],  # backend/
        env={**os.environ, "DATABASE_URL": test_db_url},
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise AssertionError(f"Migration failed: {result.stderr}")

    schema_sql_path = repo_root / "docs" / "schema.sql"
    expected = parse_schema_sql(schema_sql_path)

    with engine.connect():
        actual = inspect_db(engine)

    diffs = diff_schemas(expected, actual)
    assert not diffs, "Differences found between docs/schema.sql and migrated DB:\n" + "\n".join(
        diffs
    )


def test_no_autogenerate_diffs():
    """Ensure the current SQLAlchemy models match the migrated database schema exactly."""
    from app.models.base import Base

    test_db_url = os.environ["TEST_DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(test_db_url)

    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        diff = compare_metadata(context, Base.metadata)

        if diff:
            import pprint

            pprint.pprint(diff)
        assert not diff, f"Alembic detected schema differences between models and DB: {diff}"
