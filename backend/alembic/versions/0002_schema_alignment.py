"""Schema alignment migration: audit_events.at, entitlements.category, llm_calls columns/fks

Revision ID: 0002_schema_alignment
Revises: 0001_initial
Create Date: 2026-10-11 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_schema_alignment"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. audit_events: add column 'at' timestamptz NOT NULL DEFAULT now()
    op.add_column(
        "audit_events",
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. entitlements: category must be NULLABLE
    op.alter_column(
        "entitlements",
        "category",
        existing_type=sa.Text(),
        nullable=True,
    )

    # 3. llm_calls:
    # - add column 'task' text NOT NULL with temporary server_default 'unknown', then drop server_default
    op.add_column(
        "llm_calls",
        sa.Column(
            "task",
            sa.Text(),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.alter_column("llm_calls", "task", server_default=None)

    # - claim_id: drop NOT NULL
    op.alter_column(
        "llm_calls",
        "claim_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # - drop foreign keys llm_calls_claim_id_fkey and llm_calls_document_id_fkey
    op.drop_constraint("llm_calls_claim_id_fkey", "llm_calls", type_="foreignkey")
    op.drop_constraint("llm_calls_document_id_fkey", "llm_calls", type_="foreignkey")


def downgrade() -> None:
    # Reverse 3. llm_calls:
    # - re-create foreign keys
    op.create_foreign_key(
        "llm_calls_document_id_fkey",
        "llm_calls",
        "documents",
        ["document_id"],
        ["id"],
    )
    op.create_foreign_key(
        "llm_calls_claim_id_fkey",
        "llm_calls",
        "claims",
        ["claim_id"],
        ["id"],
    )

    # - claim_id: make NOT NULL again (setting dummy value if any null exists)
    op.alter_column(
        "llm_calls",
        "claim_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # - drop column 'task'
    op.drop_column("llm_calls", "task")

    # Reverse 2. entitlements: category NOT NULL
    op.alter_column(
        "entitlements",
        "category",
        existing_type=sa.Text(),
        nullable=False,
    )

    # Reverse 1. audit_events: drop column 'at'
    op.drop_column("audit_events", "at")
