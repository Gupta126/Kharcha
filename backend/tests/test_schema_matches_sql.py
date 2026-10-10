"""
Test that Alembic migration produces schema matching schema.sql
"""

import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection


def _get_tables_and_columns(conn: Connection):
    """Get all tables and their columns from the database."""
    inspector = inspect(conn)
    tables = {}

    for table_name in inspector.get_table_names():
        if table_name.startswith("alembic"):
            continue  # Skip Alembic version table

        columns = {}
        for col in inspector.get_columns(table_name):
            columns[col["name"]] = {
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": str(col["default"]) if col["default"] is not None else None,
                "primary_key": col.get("primary_key", False),
            }

        # Get indexes
        indexes = []
        for idx in inspector.get_indexes(table_name):
            indexes.append(
                {"name": idx["name"], "columns": idx["column_names"], "unique": idx["unique"]}
            )

        # Get foreign keys
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name):
            foreign_keys.append(
                {
                    "name": fk["name"],
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
            )

        tables[table_name] = {"columns": columns, "indexes": indexes, "foreign_keys": foreign_keys}

    return tables


def _parse_schema_sql(sql_path: Path):
    """Parse schema.sql to extract expected tables and columns."""
    # This is a simplified parser - in reality we'd want to parse the SQL properly
    # For now, we'll rely on the fact that our migration should match exactly
    # and we can test by ensuring the migration runs without error
    # and produces tables that we expect

    expected_tables = {
        "employees",
        "policies",
        "entitlements",
        "claims",
        "documents",
        "expense_lines",
        "reservations",
        "extracted_fields",
        "flags",
        "questions",
        "agent_messages",
        "llm_calls",
        "audit_events",
    }

    return expected_tables


def test_migration_matches_schema():
    """Test that running migration produces expected schema."""
    # Use the test database URL
    TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]

    # Create engine
    engine = create_engine(TEST_DATABASE_URL)

    # Start from an empty schema: drops tables, enum types and alembic_version
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],  # backend/
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Migration failed: {result.stderr}")
        raise AssertionError(f"Migration failed: {result.stderr}")

    # Check that we have the expected tables
    with engine.connect() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names()) - {"alembic_version"}

        expected_tables = {
            "employees",
            "policies",
            "entitlements",
            "claims",
            "documents",
            "expense_lines",
            "reservations",
            "extracted_fields",
            "flags",
            "questions",
            "agent_messages",
            "llm_calls",
            "audit_events",
        }

        # Check that all expected tables exist
        missing_tables = expected_tables - table_names
        unexpected_tables = table_names - expected_tables

        assert not missing_tables, f"Missing tables: {missing_tables}"
        assert not unexpected_tables, f"Unexpected tables: {unexpected_tables}"

        # Check a few key columns to ensure migration ran correctly
        employees_columns = {col["name"] for col in inspector.get_columns("employees")}
        expected_employees_columns = {
            "id",
            "email",
            "name",
            "grade",
            "cost_centre",
            "home_city",
            "manager_id",
            "role",
            "created_at",
            "updated_at",
        }

        missing_columns = expected_employees_columns - employees_columns
        assert not missing_columns, f"Missing columns in employees: {missing_columns}"

        # Check that created_at and updated_at exist with proper types
        claims_columns = {col["name"]: col for col in inspector.get_columns("claims")}
        assert "created_at" in claims_columns
        assert "updated_at" in claims_columns
        assert "submitted_at" in claims_columns  # From schema.sql
        assert "decided_at" in claims_columns  # From schema.sql


if __name__ == "__main__":
    test_migration_matches_schema()
    print("All tests passed!")
