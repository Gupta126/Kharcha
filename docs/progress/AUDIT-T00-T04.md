# Audit of Tasks T-00 to T-04

| task | Deliver item | evidence (file/function/test) | PASS/FAIL | notes |
|---|---|---|---|---|
| T-00 | `contracts/openapi.yaml` reviewed against SPEC §3 | `contracts/openapi.yaml` | PASS | Exists and contains Priya and Arjun examples |
| T-00 | Tag `contract-v1.0.0` | `git tag -l` | PASS | Tag exists |
| T-00 | `make contract-check` passes | `make contract-check` | PASS | Succeeds |
| T-00 | Prism serves every path with examples | `npx prism mock` / `curl` | FAIL | Prism mock did not start or failed to return valid JSON |
| T-01 | Directory tree from PRD §20 | `android/`, `console/` | FAIL | `android/` and `console/` directories (with READMEs) are missing |
| T-01 | `.gitignore` (Python, Android, Node, .env) | `.gitignore` | PASS | All required patterns are covered |
| T-01 | `pyproject.toml` in python projects | `*/pyproject.toml` | PASS | Exist in backend, forensics, mock-erp, eval with ruff/mypy/pytest |
| T-01 | `README.md` with quick start | `README.md` | PASS | Quick start section is present |
| T-01 | Keep existing kit files unchanged | `contracts/openapi.yaml`, `docs/SPEC.md` | PASS | Kit files preserved |
| T-01 | `make help` and `uv sync` | Makefile, uv | PASS | Both commands succeed |
| T-01 | `ruff check` in backend | `uv run ruff check` | FAIL | Ruff check failed in backend |
| T-02 | `backend/app/main.py` (FastAPI, `/v1` prefix) | `backend/app/main.py` | PASS | Exists and uses FastAPI with /v1 prefix |
| T-02 | `core/settings.py` (all .env keys) | `backend/app/core/settings.py` | PASS | Declares all required keys |
| T-02 | `core/errors.py` (SPEC §2 format + handlers) | `backend/app/core/errors.py` | PASS | Error handlers and envelope are present |
| T-02 | `api/health.py` (checks db/redis/erp/llm) | `backend/app/api/health.py` | PASS | Route `/healthz` exists and checks services |
| T-02 | `backend/Dockerfile` | `backend/Dockerfile` | PASS | Uses `python:3.12-slim` |
| T-02 | tests for healthz and error format | `backend/tests/` | FAIL | No test files cover healthz or SPEC §2 errors |
| T-02 | `tests/test_contract.py` | `backend/tests/test_contract.py` | FAIL | File is missing |
| T-02 | `pytest` passes with tests | `pytest` | FAIL | 0 tests collected, expected >= 1 |
| T-03 | `mock-erp/app/main.py` with endpoints | `mock-erp/app/main.py` | PASS | File exists and references seed data |
| T-03 | loading `data/seed/employees.json` | `data/seed/employees.json` | PASS | Seed data is present and loaded |
| T-03 | in-memory store | Test behavior | PASS | Database-less operation verified by tests |
| T-03 | status timeline | `mock-erp/app/` | PASS | Status transitions configured |
| T-03 | `POST /admin/scenario` | `mock-erp/app/api/admin.py` | PASS | Endpoint is present |
| T-03 | `Dockerfile` | `mock-erp/Dockerfile` | PASS | Exists and uses `python:3.12` |
| T-03 | tests covering specs | `mock-erp/tests/` | PASS | 17 tests passing, covering Arjun and submissions |
| T-03 | Docker build and run | `docker build` / `/health` | PASS | Container builds and responds on `/health` |
| T-04 | SQLAlchemy 2 models in `backend/app/models/` | `backend/app/models/` | FAIL | Models exist but do not use SQLAlchemy 2 style (`Mapped`/`mapped_column`) |
| T-04 | Alembic env + migration `0001_initial` | `backend/alembic/` | PASS | Exists and migration is created |
| T-04 | Models include `created_at/updated_at` | `backend/app/models/base.py` | PASS | Base model includes these columns |
| T-04 | async session factory | `backend/app/db/session.py` | PASS | Uses `AsyncSession` |
| T-04 | migration equal to `docs/schema.sql` | `test_schema_matches_sql.py` | PASS | Migration passes the schema match test |
