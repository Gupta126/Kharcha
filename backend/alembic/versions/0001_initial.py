"""Initial migration

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types first
    claim_status_enum = postgresql.ENUM('draft', 'needs_info', 'ready', 'submitted', 'in_review',
                                       'approved', 'rejected', 'returned', 'paid', name='claim_status')
    claim_status_enum.create(op.get_bind())

    expense_category_enum = postgresql.ENUM('flight', 'rail', 'cab', 'hotel', 'meal', 'fuel', 'toll',
                                           'telecom', 'broadband', 'other', name='expense_category')
    expense_category_enum.create(op.get_bind())

    flag_type_enum = postgresql.ENUM('policy', 'entitlement', 'duplicate', 'authenticity', 'missing', name='flag_type')
    flag_type_enum.create(op.get_bind())

    severity_enum = postgresql.ENUM('green', 'amber', 'red', name='severity')
    severity_enum.create(op.get_bind())

    period_kind_enum = postgresql.ENUM('month', 'quarter', 'fin_year', 'per_trip', name='period_kind')
    period_kind_enum.create(op.get_bind())

    # Create tables

    # Create tables
    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('grade', sa.String(length=50), nullable=False),
        sa.Column('cost_centre', sa.String(length=100)),
        sa.Column('home_city', sa.String(length=100)),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True)),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='employee'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_employees_email'), 'employees', ['email'], unique=True)

    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('rules', sa.Text(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )

    op.create_table(
        'entitlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('overall', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('period', postgresql.ENUM('month', 'quarter', 'fin_year', 'per_trip', name='period_kind', create_type=False), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('limit_paise', sa.BigInteger(), nullable=False),
        sa.Column('paid_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'category', 'period_start')
    )

    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('trip_start', sa.Date()),
        sa.Column('trip_end', sa.Date()),
        sa.Column('city', sa.Text()),
        sa.Column('status', postgresql.ENUM('draft', 'needs_info', 'ready', 'submitted', 'in_review',
                                           'approved', 'rejected', 'returned', 'paid', name='claim_status', create_type=False), nullable=False, server_default='draft'),
        sa.Column('total_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True)),
        sa.Column('erp_ref', sa.Text()),
        sa.Column('submitted_at', sa.DateTime(timezone=True)),
        sa.Column('decided_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approver_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_claims_employee_id_status'), 'claims', ['employee_id', 'status'], unique=False)

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True)),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('phash', sa.BigInteger()),
        sa.Column('fuzzy_key', sa.Text()),
        sa.Column('mime', sa.Text(), nullable=False),
        sa.Column('pages', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('capture_source', sa.Text(), nullable=False),
        sa.Column('storage_uri', sa.Text()),
        sa.Column('trust_score', sa.Integer()),
        sa.Column('device_tier', sa.String(length=1)),
        sa.Column('prompt_version', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'sha256')
    )
    op.create_index(op.f('ix_documents_fuzzy_key'), 'documents', ['fuzzy_key'], unique=False)
    op.create_index(op.f('ix_documents_phash'), 'documents', ['phash'], unique=False)

    op.create_table(
        'expense_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True)),
        sa.Column('category', postgresql.ENUM('flight', 'rail', 'cab', 'hotel', 'meal', 'fuel', 'toll',
                                             'telecom', 'broadband', 'other', name='expense_category', create_type=False), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('vendor', sa.Text()),
        sa.Column('city', sa.Text()),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('claimable_paise', sa.BigInteger(), nullable=False),
        sa.Column('cgst_paise', sa.BigInteger()),
        sa.Column('sgst_paise', sa.BigInteger()),
        sa.Column('igst_paise', sa.BigInteger()),
        sa.Column('gstin', sa.Text()),
        sa.Column('purpose', sa.Text()),
        sa.Column('attendees', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('excluded_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expense_lines_claim_id'), 'expense_lines', ['claim_id'], unique=False)

    op.create_table(
        'reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entitlement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['entitlement_id'], ['entitlements.id'], ),
        sa.ForeignKeyConstraint(['line_id'], ['expense_lines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('held','released','consumed')", name='reservations_status_check')
    )
    op.create_index(op.f('ix_reservations_entitlement_id_status'), 'reservations', ['entitlement_id', 'status'], unique=False)

    op.create_table(
        'extracted_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('confidence', sa.REAL(), nullable=False),
        sa.Column('bbox', sa.Text()),  # Storing as text for simplicity, could be array
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True)),
        sa.Column('document_id', postgresql.UUID(as_uuid=True)),
        sa.Column('type', postgresql.ENUM('policy', 'entitlement', 'duplicate', 'authenticity', 'missing', name='flag_type', create_type=False), nullable=False),
        sa.Column('severity', postgresql.ENUM('green', 'amber', 'red', name='severity', create_type=False), nullable=False),
        sa.Column('rule_id', sa.Text()),
        sa.Column('policy_version', sa.Integer()),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('status', sa.Text(), nullable=False, server_default='open'),
        sa.Column('resolution_note', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['line_id'], ['expense_lines.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True)),
        sa.Column('field', sa.Text(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('options', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('answer', sa.Text()),
        sa.Column('asked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('answered_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['line_id'], ['expense_lines.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'agent_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE')
    )

    op.create_table(
        'llm_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True)),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('tokens_in', sa.Integer()),
        sa.Column('tokens_out', sa.Integer()),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('failure', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'])
    )

    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True)),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('target_type', sa.Text(), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('before', sa.Text()),
        sa.Column('after', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('audit_events')
    op.drop_table('llm_calls')
    op.drop_table('agent_messages')
    op.drop_table('questions')
    op.drop_table('flags')
    op.drop_table('extracted_fields')
    op.drop_table('reservations')
    op.drop_table('expense_lines')
    op.drop_table('documents')
    op.drop_table('claims')
    op.drop_table('entitlements')
    op.drop_table('policies')
    op.drop_table('employees')

    # Drop ENUM types
    sa.Enum(name='claim_status').drop(op.get_bind())
    sa.Enum(name='expense_category').drop(op.get_bind())
    sa.Enum(name='flag_type').drop(op.get_bind())
    sa.Enum(name='severity').drop(op.get_bind())
    sa.Enum(name='period_kind').drop(op.get_bind())
    # ### end Alembic commands ###
