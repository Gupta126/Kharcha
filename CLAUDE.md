# Kharcha — AI expense & reimbursement agent

Monorepo for a hackathon prototype: Android app + Python backend + mock finance (ERP).
Turns a pile of receipts into a verified, policy-checked, submit-ready claim.
All data is synthetic. The finance system is mocked. Never use real receipts or real company data.

## Source of truth
- Product + design: docs/PRD.md (text version of docs/PRD.pdf). Sections are headed "## PRD §n"; read only the sections a task references. Never open docs/PRD.pdf.
- Locked decisions, contracts and algorithms: @docs/SPEC.md  (wins over the PDF if they ever differ)
- Work breakdown: @docs/TASKS.md  — implement ONE task per session, in dependency order.
- Database: docs/schema.sql (Alembic migrations must produce exactly this schema).
- API contract: contracts/openapi.yaml (paths include /v1). Receipt JSON contract: contracts/receipt.schema.json
- Shared test vectors for Kotlin AND Python: contracts/test-vectors/*.json

## Two workspaces (read CLAUDE.local.md first)
Development is split across two machines that share this one repository through GitHub:
- **APP** workspace = laptop: `android/`, `console/`. Guide: docs/workspaces/APP.md
- **BACKEND** workspace = Oracle kh-core VM (arm64) — the same VM also hosts the live backend: `backend/`, `forensics/`, `mock-erp/`, `gateway/`, `eval/`, `data/`, `deploy/`, `contracts/`. Guide: docs/workspaces/BACKEND.md
- Each machine has an untracked `CLAUDE.local.md` (copied from docs/workspaces/CLAUDE.local.*.md) naming its workspace.
  If CLAUDE.local.md is missing, ask which workspace this is before doing anything.
- `contracts/` (OpenAPI, receipt schema, test vectors, shared prompts) is the only shared surface. BACKEND owns it;
  APP requests changes in docs/CONTRACT_REQUESTS.md. Never change both sides of the contract in one commit.
- Only touch folders your workspace owns. Each task in docs/TASKS.md says its Workspace.

## Stack (do not substitute without asking)
- backend/, forensics/, mock-erp/, gateway/: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2,
  RQ + Redis, PostgreSQL 16, local file storage for originals (STORAGE_DIR, behind a Storage interface). Tooling: uv, ruff, mypy, pytest.
- android/: Kotlin 2.x, Jetpack Compose, Hilt, Room (KSP), WorkManager, Retrofit + kotlinx.serialization,
  ML Kit (Document Scanner, Text Recognition v2, GenAI Prompt API), LiteRT-LM. Package: ai.kharcha.
  minSdk 26, compileSdk/targetSdk = latest stable. Gradle version catalog (libs.versions.toml).
- console/: React + Vite + TypeScript, built to static files.
- LLMs: NVIDIA hosted models only, via the LiteLLM gateway task aliases (kh-extract-image, kh-extract-text, kh-agent, kh-parse).
  No local model on the VM. When NVIDIA fails, use the no-LLM degraded mode in SPEC §6.
- Claude Code is used as the terminal CLI on both machines.

## Commands
- BACKEND: `make dev-api` (127.0.0.1:8001), `make dev-worker`, `make migrate-dev`, `make seed-dev`, `make infra-up SVC="..."`, `make status`, `make llm-smoke`
- APP: `./scripts/mock-api.sh` (Prism mock :4010), `./scripts/tunnel.sh` (reach kh-core dev stack), `./scripts/app-dev-connect.sh`
- Both: `make contract-check`
- `make backend-test`                  ruff + mypy + pytest for backend, forensics, mock-erp
- `make android-test`                  ./gradlew :app:testDebugUnitTest lint
- `make eval`                          python eval/run_eval.py --alias all
Each task in docs/TASKS.md lists its own verify commands. A task is done only when they pass.

## Rules
- Money is integer paise (BIGINT / Long). Dates ISO 8601. IDs UUIDv7 strings.
- Never commit secrets. Only .env.example is committed. Do not print key values in logs or output.
- Never call an LLM vendor directly from code; use LLMGateway (backend) or ReceiptExtractor (android).
- The LLM never computes money, limits or policy outcomes — deterministic code does; the LLM extracts and words.
- Validation logic must pass contracts/test-vectors in both languages.
- Keep changes scoped to the current task. If the spec is ambiguous, stop and ask; do not invent requirements.
- Write tests with the code. Run the task's verify commands before saying a task is done.
- This VM also runs **Apache Guacamole** (Docker) and **host nginx** (80/443) that are not part of Kharcha. Never stop, restart,
  reconfigure or remove them, their containers, volumes or networks, never edit /etc/nginx, and never run
  `docker system prune`, `docker compose down` without `-p kharcha`, or `systemctl restart docker`.
- The hosted stack in /opt/kharcha is the live demo on this same VM. Never edit /opt/kharcha, never run `make deploy`,
  and never stop/restart/down the `kharcha` compose project unless explicitly asked. `make infra-up` is allowed.
- Development uses the dev checkout ~/kharcha, `.env.dev`, `kharcha_dev`/`kharcha_test` databases and port 8001 only.
- Steps marked HUMAN in docs/TASKS.md (cloud console, API keys, DNS, phone testing) are not yours to do;
  prepare scripts/instructions and stop.

## Finishing a task
1. Verify commands pass.  2. Update the task's checkbox in docs/TASKS.md.
3. Short summary: files changed, how verified, anything left open.
