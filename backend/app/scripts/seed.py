import argparse
import asyncio
import json
import logging

import uuid6
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_db(employees_path: str, policy_path: str):
    engine = create_async_engine(str(settings.DATABASE_URL))

    with open(employees_path) as f:
        emp_data = json.load(f)

    with open(policy_path) as f:
        policy_data = json.load(f)

    async with engine.begin() as conn:
        # Seed Policy
        version = policy_data.get("version", 1)
        effective_from = policy_data.get("effective_from")
        # Ensure active

        await conn.execute(
            text("""
            INSERT INTO policies
                (id, version, rules, effective_from, active, created_at, updated_at)
            VALUES (:id, :version, :rules, :effective_from, :active, now(), now())
            ON CONFLICT (version) DO UPDATE SET
                rules = EXCLUDED.rules,
                effective_from = EXCLUDED.effective_from,
                active = EXCLUDED.active,
                updated_at = now()
            """),
            {
                "id": str(uuid6.uuid7()),
                "version": version,
                "rules": json.dumps(policy_data.get("rules", [])),
                "effective_from": effective_from,
                "active": True,
            },
        )

        # Build employees map for manager linking
        email_to_id = {emp["email"]: emp["id"] for emp in emp_data.get("employees", [])}

        # First pass: Insert all employees without manager_id to avoid FK violations
        for emp in emp_data.get("employees", []):
            emp_id = emp["id"]

            await conn.execute(
                text("""
                INSERT INTO employees
                    (id, email, name, grade, cost_centre, home_city, manager_id, role,
                     created_at, updated_at)
                VALUES (:id, :email, :name, :grade, :cost_centre, :home_city, NULL, :role,
                        now(), now())
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    grade = EXCLUDED.grade,
                    cost_centre = EXCLUDED.cost_centre,
                    home_city = EXCLUDED.home_city,
                    role = EXCLUDED.role,
                    updated_at = now()
                """),
                {
                    "id": emp_id,
                    "email": emp["email"],
                    "name": emp["name"],
                    "grade": emp["grade"],
                    "cost_centre": emp.get("cost_centre"),
                    "home_city": emp.get("home_city"),
                    "role": emp.get("role", "employee"),
                },
            )

        # Second pass: Update manager_id and insert entitlements
        for emp in emp_data.get("employees", []):
            emp_id = emp["id"]
            manager_email = emp.get("manager_email")
            manager_id = email_to_id.get(manager_email) if manager_email else None

            if manager_id:
                await conn.execute(
                    text("UPDATE employees SET manager_id = :manager_id WHERE id = :id"),
                    {"manager_id": manager_id, "id": emp_id},
                )

            # Seed Entitlements
            for ent in emp.get("entitlements", []):
                # We need a unique constraint on (employee_id, category, period_start)
                # to do an upsert
                await conn.execute(
                    text("""
                    INSERT INTO entitlements
                        (id, employee_id, category, overall, period, period_start, period_end,
                         limit_paise, paid_paise, fetched_at, created_at, updated_at)
                    VALUES (:id, :employee_id, :category, :overall, :period, :period_start,
                            :period_end, :limit_paise, :paid_paise, now(), now(), now())
                    ON CONFLICT (employee_id, category, period_start) DO UPDATE SET
                        overall = EXCLUDED.overall,
                        period = EXCLUDED.period,
                        period_end = EXCLUDED.period_end,
                        limit_paise = EXCLUDED.limit_paise,
                        paid_paise = EXCLUDED.paid_paise,
                        fetched_at = now(),
                        updated_at = now()
                    """),
                    {
                        "id": str(uuid6.uuid7()),
                        "employee_id": emp_id,
                        "category": ent.get("category"),
                        "overall": ent.get("overall", False),
                        "period": ent.get("period"),
                        "period_start": ent.get("period_start"),
                        "period_end": ent.get("period_end"),
                        "limit_paise": ent.get("limit_paise", 0),
                        "paid_paise": ent.get("paid_paise", 0),
                    },
                )

    await engine.dispose()
    logger.info("Database seeded successfully.")


def main():
    parser = argparse.ArgumentParser(description="Seed Kharcha Database")
    parser.add_argument("--employees", required=True, help="Path to employees JSON")
    parser.add_argument("--policy", required=True, help="Path to policy JSON")
    args = parser.parse_args()

    asyncio.run(seed_db(args.employees, args.policy))


if __name__ == "__main__":
    main()
