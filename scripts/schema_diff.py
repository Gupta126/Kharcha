#!/usr/bin/env python3
"""scripts/schema_diff.py

Compares PostgreSQL database schema against docs/schema.sql.
Exits 0 if no differences, non-zero if differences are detected.

Usage:
  python3 scripts/schema_diff.py <database_name_or_url>
"""

import os
import re
import sys
from pathlib import Path

# Ensure backend virtualenv dependencies (sqlalchemy, psycopg, etc.) can be imported
_repo_root = Path(__file__).resolve().parent.parent
_backend_venv_lib = _repo_root / "backend" / ".venv" / "lib"
if _backend_venv_lib.exists():
    for _p in _backend_venv_lib.glob("python3.*/site-packages"):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))

from typing import Any

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect


def parse_schema_sql(sql_path: Path) -> dict[str, Any]:
    """Parse CREATE TABLE statements in docs/schema.sql."""
    content = sql_path.read_text(encoding="utf-8")

    # Match CREATE TABLE <name> (...)
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+([a-zA-Z0-9_]+)\s*\((.*?)\);",
        re.DOTALL | re.IGNORECASE,
    )

    expected_tables: dict[str, dict[str, Any]] = {}

    for match in table_pattern.finditer(content):
        table_name = match.group(1).lower()
        body = match.group(2).strip()

        # Split items by comma, but be careful with parentheses and checks
        items = _split_table_items(body)

        columns: dict[str, dict[str, Any]] = {}
        foreign_keys: list[dict[str, Any]] = []

        for item in items:
            item_clean = " ".join(item.strip().split())
            if not item_clean:
                continue

            # Check if this item is a table-level constraint
            if re.match(r"^(PRIMARY\s+KEY|UNIQUE|CHECK|FOREIGN\s+KEY)\b", item_clean, re.I):
                # Table level constraint
                fk_match = re.search(
                    r"FOREIGN\s+KEY\s*\((.*?)\)\s*REFERENCES\s+([a-zA-Z0-9_]+)\s*\((.*?)\)(?:\s+ON\s+DELETE\s+(CASCADE|SET\s+NULL|RESTRICT))?",
                    item_clean,
                    re.I,
                )
                if fk_match:
                    foreign_keys.append({
                        "constrained_columns": [c.strip().lower() for c in fk_match.group(1).split(",")],
                        "referred_table": fk_match.group(2).lower(),
                        "referred_columns": [c.strip().lower() for c in fk_match.group(3).split(",")],
                        "on_delete": fk_match.group(4).upper() if fk_match.group(4) else "NO ACTION",
                    })
                continue

            # Column definition: e.g. "id uuid PRIMARY KEY"
            # "category expense_category"
            # "claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE"
            col_parts = item_clean.split()
            col_name = col_parts[0].lower()

            is_not_null = bool(re.search(r"\bNOT\s+NULL\b", item_clean, re.I)) or bool(
                re.search(r"\bPRIMARY\s+KEY\b", item_clean, re.I)
            )

            columns[col_name] = {
                "not_null": is_not_null,
            }

            # Inline foreign key: REFERENCES target(col) [ON DELETE CASCADE]
            ref_match = re.search(
                r"REFERENCES\s+([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?(?:\s+ON\s+DELETE\s+(CASCADE|SET\s+NULL|RESTRICT))?",
                item_clean,
                re.I,
            )
            if ref_match:
                ref_table = ref_match.group(1).lower()
                ref_col = ref_match.group(2).lower() if ref_match.group(2) else "id"
                on_delete = ref_match.group(3).upper() if ref_match.group(3) else "NO ACTION"
                foreign_keys.append({
                    "constrained_columns": [col_name],
                    "referred_table": ref_table,
                    "referred_columns": [ref_col],
                    "on_delete": on_delete,
                })

        expected_tables[table_name] = {
            "columns": columns,
            "foreign_keys": foreign_keys,
        }

    return expected_tables


def _split_table_items(body: str) -> list[str]:
    """Split comma-separated table column/constraint definitions respecting parentheses."""
    items = []
    current: list[str] = []
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        items.append("".join(current).strip())
    return items


def inspect_db(engine) -> dict[str, Any]:
    """Inspect actual database schema."""
    inspector = inspect(engine)
    actual_tables: dict[str, Any] = {}

    for table_name in inspector.get_table_names():
        if table_name == "alembic_version":
            continue

        columns: dict[str, dict[str, Any]] = {}
        for col in inspector.get_columns(table_name):
            cname = col["name"].lower()
            columns[cname] = {
                "not_null": not col["nullable"],
            }

        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            options = fk.get("options", {})
            on_delete = (options.get("ondelete") or "NO ACTION").upper()
            fks.append({
                "constrained_columns": [c.lower() for c in fk["constrained_columns"]],
                "referred_table": fk["referred_table"].lower(),
                "referred_columns": [c.lower() for c in fk["referred_columns"]],
                "on_delete": on_delete,
            })

        actual_tables[table_name.lower()] = {
            "columns": columns,
            "foreign_keys": fks,
        }

    return actual_tables


def diff_schemas(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Return differences between expected and actual schemas."""
    errors = []

    # Extra timestamps allowed by schema.sql docstring:
    allowed_extras = {"created_at", "updated_at"}

    # 1. Table presence
    expected_tables = set(expected.keys())
    actual_tables = set(actual.keys())

    missing_tables = expected_tables - actual_tables
    if missing_tables:
        errors.append(f"Missing tables in DB: {missing_tables}")

    unexpected_tables = actual_tables - expected_tables
    if unexpected_tables:
        errors.append(f"Unexpected tables in DB: {unexpected_tables}")

    for tname in expected_tables & actual_tables:
        exp_table = expected[tname]
        act_table = actual[tname]

        # Columns
        exp_cols = exp_table["columns"]
        act_cols = act_table["columns"]

        missing_cols = set(exp_cols.keys()) - set(act_cols.keys())
        if missing_cols:
            errors.append(f"Table '{tname}': missing columns {missing_cols}")

        extra_cols = set(act_cols.keys()) - set(exp_cols.keys()) - allowed_extras
        if extra_cols:
            errors.append(f"Table '{tname}': unexpected columns {extra_cols}")

        # Check nullability
        for cname in set(exp_cols.keys()) & set(act_cols.keys()):
            exp_nn = exp_cols[cname]["not_null"]
            act_nn = act_cols[cname]["not_null"]
            if exp_nn != act_nn:
                errors.append(
                    f"Table '{tname}', column '{cname}': nullability mismatch. "
                    f"Expected NOT NULL={exp_nn}, got NOT NULL={act_nn}"
                )

        # Foreign keys
        exp_fks = exp_table["foreign_keys"]
        act_fks = act_table["foreign_keys"]

        for efk in exp_fks:
            matched = False
            for afk in act_fks:
                if (
                    efk["constrained_columns"] == afk["constrained_columns"]
                    and efk["referred_table"] == afk["referred_table"]
                    and efk["referred_columns"] == afk["referred_columns"]
                ):
                    matched = True
                    if efk["on_delete"] != afk["on_delete"]:
                        errors.append(
                            f"Table '{tname}': FK on {efk['constrained_columns']} ON DELETE mismatch. "
                            f"Expected {efk['on_delete']}, got {afk['on_delete']}"
                        )
                    break
            if not matched:
                errors.append(
                    f"Table '{tname}': Missing expected FK from {efk['constrained_columns']} to "
                    f"{efk['referred_table']}({efk['referred_columns']})"
                )

        # Check for unexpected FKs (e.g. llm_calls having FKs when schema.sql has none)
        for afk in act_fks:
            matched = False
            for efk in exp_fks:
                if (
                    afk["constrained_columns"] == efk["constrained_columns"]
                    and afk["referred_table"] == efk["referred_table"]
                    and afk["referred_columns"] == efk["referred_columns"]
                ):
                    matched = True
                    break
            if not matched:
                errors.append(
                    f"Table '{tname}': Unexpected FK on {afk['constrained_columns']} to "
                    f"{afk['referred_table']}({afk['referred_columns']})"
                )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/schema_diff.py <database_name_or_url>")
        return 1

    target = sys.argv[1]
    repo_root = Path(__file__).resolve().parent.parent

    # Resolve database URL
    db_url = target
    if not (target.startswith("postgresql://") or target.startswith("postgres://")):
        env_path = repo_root / ".env.dev"
        env_vals = dotenv_values(env_path) if env_path.exists() else {}
        base_url = env_vals.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not base_url:
            print(f"Error: DATABASE_URL not set and target '{target}' is not a full URL")
            return 1
        base_url = base_url.replace("+asyncpg", "")
        # replace database name in URL
        parts = base_url.rsplit("/", 1)
        db_url = f"{parts[0]}/{target}"
    else:
        db_url = db_url.replace("+asyncpg", "")

    schema_sql_path = repo_root / "docs" / "schema.sql"
    if not schema_sql_path.exists():
        print(f"Error: schema.sql not found at {schema_sql_path}")
        return 1

    expected = parse_schema_sql(schema_sql_path)
    engine = create_engine(db_url)
    with engine.connect():
        actual = inspect_db(engine)

    diffs = diff_schemas(expected, actual)
    if diffs:
        print(f"FAILED: Found {len(diffs)} difference(s) between docs/schema.sql and database '{target}':")
        for d in diffs:
            print(f"  - {d}")
        return 1

    print(f"OK: Database '{target}' matches docs/schema.sql exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
