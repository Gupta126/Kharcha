-- Kharcha PostgreSQL schema (PRD §23). Alembic migration 0001 must produce exactly this,
-- plus created_at/updated_at timestamptz NOT NULL DEFAULT now() on every table that lacks them.

CREATE TYPE claim_status AS ENUM ('draft','needs_info','ready','submitted','in_review',
                                  'approved','rejected','returned','paid');
CREATE TYPE expense_category AS ENUM ('flight','rail','cab','hotel','meal','fuel','toll',
                                      'telecom','broadband','other');
CREATE TYPE flag_type AS ENUM ('policy','entitlement','duplicate','authenticity','missing');
CREATE TYPE severity AS ENUM ('green','amber','red');
CREATE TYPE period_kind AS ENUM ('month','quarter','fin_year','per_trip');

CREATE TABLE employees (
  id uuid PRIMARY KEY, email text UNIQUE NOT NULL, name text NOT NULL,
  grade text NOT NULL, cost_centre text, home_city text,
  manager_id uuid REFERENCES employees(id), role text NOT NULL DEFAULT 'employee');

CREATE TABLE policies (
  id uuid PRIMARY KEY, version int UNIQUE NOT NULL, rules jsonb NOT NULL,
  effective_from date NOT NULL, active boolean NOT NULL DEFAULT false);

CREATE TABLE entitlements (
  id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
  category expense_category, overall boolean NOT NULL DEFAULT false,
  period period_kind NOT NULL, period_start date NOT NULL, period_end date NOT NULL,
  limit_paise bigint NOT NULL CHECK (limit_paise >= 0),
  paid_paise bigint NOT NULL DEFAULT 0, fetched_at timestamptz NOT NULL,
  UNIQUE (employee_id, category, period_start));

CREATE TABLE claims (
  id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
  title text, trip_start date, trip_end date, city text,
  status claim_status NOT NULL DEFAULT 'draft',
  total_paise bigint NOT NULL DEFAULT 0, approver_id uuid REFERENCES employees(id),
  erp_ref text, submitted_at timestamptz, decided_at timestamptz);
CREATE INDEX ON claims (employee_id, status);

CREATE TABLE documents (
  id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
  claim_id uuid REFERENCES claims(id), sha256 char(64) NOT NULL, phash bigint,
  fuzzy_key text, mime text NOT NULL, pages int NOT NULL DEFAULT 1,
  capture_source text NOT NULL, storage_uri text, trust_score smallint,
  device_tier char(1), prompt_version text,
  UNIQUE (employee_id, sha256));
CREATE INDEX ON documents (fuzzy_key);
CREATE INDEX ON documents (phash);

CREATE TABLE expense_lines (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  document_id uuid REFERENCES documents(id), category expense_category NOT NULL,
  expense_date date NOT NULL, vendor text, city text,
  amount_paise bigint NOT NULL, claimable_paise bigint NOT NULL,
  cgst_paise bigint, sgst_paise bigint, igst_paise bigint, gstin text,
  purpose text, attendees jsonb NOT NULL DEFAULT '[]', excluded_reason text);
CREATE INDEX ON expense_lines (claim_id);

CREATE TABLE reservations (
  id uuid PRIMARY KEY, entitlement_id uuid NOT NULL REFERENCES entitlements(id),
  line_id uuid NOT NULL REFERENCES expense_lines(id) ON DELETE CASCADE,
  amount_paise bigint NOT NULL,
  status text NOT NULL CHECK (status IN ('held','released','consumed')));
CREATE INDEX ON reservations (entitlement_id, status);

CREATE TABLE extracted_fields (
  id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  name text NOT NULL, value jsonb NOT NULL, confidence real NOT NULL,
  bbox int[4], source text NOT NULL CHECK (source IN ('ocr','llm','user','inferred')));

CREATE TABLE flags (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  line_id uuid REFERENCES expense_lines(id), document_id uuid REFERENCES documents(id),
  type flag_type NOT NULL, severity severity NOT NULL, rule_id text,
  policy_version int, message text NOT NULL, evidence jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'open', resolution_note text);

CREATE TABLE questions (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  line_id uuid REFERENCES expense_lines(id), field text NOT NULL, prompt text NOT NULL,
  options jsonb NOT NULL DEFAULT '[]', answer jsonb,
  asked_at timestamptz NOT NULL DEFAULT now(), answered_at timestamptz);

CREATE TABLE agent_messages (
  id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  role text NOT NULL, content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE llm_calls (
  id uuid PRIMARY KEY, task text NOT NULL, provider text NOT NULL, model text NOT NULL,
  claim_id uuid, document_id uuid, latency_ms int, tokens_in int, tokens_out int,
  success boolean NOT NULL, failure text, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE audit_events (
  id uuid PRIMARY KEY, actor_id uuid, action text NOT NULL, target_type text NOT NULL,
  target_id uuid NOT NULL, before jsonb, after jsonb, at timestamptz NOT NULL DEFAULT now());
