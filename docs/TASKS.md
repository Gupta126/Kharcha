# Kharcha — task board for Claude Code

Two workspaces share this repo (see CLAUDE.md and docs/workspaces/): **APP** = laptop (android/, console/),
**BACKEND** = Oracle kh-core VM (everything else, including contracts/). Run each task in the workspace it names.

## Start here (order)
1. HUMAN: H-01 Oracle VM (kh-core) → H-08 Claude Code + checkouts on kh-core → H-09 laptop setup.
2. BACKEND: T-00 then T-01. Push.
3. Then two tracks run in parallel: BACKEND T-02… and APP T-20… (the app uses the Prism mock until the backend is ready).
4. Integration points (both tracks must be done): T-25 dev check, T-27 dev check, T-31.

How to use: start a fresh Claude Code session in the repo root for each task and say
> "Read CLAUDE.md. Implement task T-xx from docs/TASKS.md only. Plan first, then build, then run its Verify commands and report."
Work in ID order unless "Depends" says otherwise. Mark `[x]` only after every Verify command passes.
Owner: **CLAUDE** = Claude Code does it end to end; **HUMAN** = you do it (console, keys, DNS, devices);
**HUMAN-VERIFY** = Claude Code builds it with fakes/tests, you confirm on a real phone or VM.
Refs: PRD §n = section "## PRD §n" in docs/PRD.md (never the PDF); SPEC §n = docs/SPEC.md section.

---
## Phase 0 — Foundations

### [x] T-00 Contract v1 freeze — CLAUDE
Workspace: BACKEND | Depends: — | Refs: contracts/README.md, SPEC §1b, §3
Deliver: review contracts/openapi.yaml against SPEC §3 and fix gaps; add realistic `examples` for ClaimView, Entitlements
(Priya's draft trip, Arjun's exhausted broadband) so the Prism mock is useful to the app; tag `contract-v1.0.0`.
Done when: `make contract-check` passes; Prism serves every path with examples.
Verify: `make contract-check && npx -y @stoplight/prism-cli@5 mock contracts/openapi.yaml -p 4010 & sleep 15 && curl -sf localhost:4010/v1/entitlements -H 'Authorization: Bearer x'`

### [x] T-01 Repo scaffold and tooling — CLAUDE
Workspace: BACKEND | Depends: — | Refs: PRD §20, CLAUDE.md
Deliver: directory tree from PRD §20 (android/ and console/ only as empty placeholders with a README); `.gitignore` (Python, Android, Node, .env); `backend/pyproject.toml`,
`forensics/pyproject.toml`, `mock-erp/pyproject.toml`, `eval/pyproject.toml` (uv, ruff, mypy, pytest);
`README.md` with quick start; keep existing kit files unchanged.
Done when: `make help` lists commands; `uv sync` succeeds in each Python project.
Verify: `make help && (cd backend && uv sync && uv run ruff check .)`

### [ ] T-02 Backend skeleton — CLAUDE
Workspace: BACKEND | Depends: T-01 | Refs: PRD §22, SPEC §1–2
Deliver: `backend/app/main.py` (FastAPI, `/v1` prefix), `core/settings.py` (pydantic-settings, all .env keys),
`core/errors.py` (SPEC §2 format + exception handlers), `api/health.py` (`GET /v1/healthz`, checks db/redis/erp/llm),
`backend/Dockerfile` (python:3.12-slim, builds on the arm64 VM), tests for healthz and error format,
`tests/test_contract.py` that compares implemented FastAPI routes/response models with contracts/openapi.yaml (skips paths not built yet, fails on mismatches).
Done when: healthz returns the SPEC shape; unknown route returns the SPEC error JSON.
Verify: `cd backend && uv run pytest -q`

### [ ] T-03 Mock ERP service — CLAUDE
Workspace: BACKEND | Depends: T-01 | Refs: PRD §22 (Mock ERP contract), SPEC §7
Deliver: `mock-erp/app/main.py` with endpoints from PRD §22, loading `data/seed/employees.json`;
in-memory store; status timeline (submitted→in_review 10 s→approved 20 s→paid 30 s, configurable);
`POST /admin/scenario`; Dockerfile; tests.
Done when: Arjun's broadband shows paid = limit; a posted reimbursement reaches `paid` on the timer.
Verify: `cd mock-erp && uv run pytest -q`

### [ ] T-04 Database models and migration — CLAUDE
Workspace: BACKEND | Depends: T-02 | Refs: PRD §23, docs/schema.sql
Deliver: SQLAlchemy 2 models in `backend/app/models/`, Alembic env + migration `0001_initial` equal to
docs/schema.sql (+ created_at/updated_at); async session factory.
Done when: migration on an empty DB gives exactly the tables, enums and indexes in schema.sql.
Verify: `make migrate-dev && cd backend && uv run --env-file ../.env.dev pytest -q tests/test_schema_matches_sql.py`

### [ ] T-05 Seed script and mock auth — CLAUDE
Workspace: BACKEND | Depends: T-03, T-04 | Refs: SPEC §1, §7
Deliver: `app/scripts/seed.py` (employees, policy v1, entitlements copied from mock ERP),
`api/auth.py` (`POST /v1/auth/login`), JWT dependency with roles.
Done when: login as each demo user returns a token; protected route rejects missing token with UNAUTHORIZED.
Verify: `make seed-dev && cd backend && uv run --env-file ../.env.dev pytest -q tests/test_auth.py`

### [ ] T-06 Server stack and dev runner — CLAUDE
Workspace: BACKEND | Depends: T-02, T-03 | Refs: deploy/server/docker-compose.yml, Makefile, SPEC §1, docs/workspaces/BACKEND.md
Deliver: forensics placeholder app with `/health`; mock-erp and gateway Dockerfiles; settings support QUEUE_PREFIX and
TEST_DATABASE_URL; `make dev-api` / `make dev-worker` run against .env.dev. Merge to main, then `make infra-up SVC="postgres redis mock-erp forensics litellm"`.
Done when: dev API on 127.0.0.1:8001 reports db/redis/erp ok; hosted compose file passes `config`.
Verify: `docker compose --env-file .env.example -f deploy/server/docker-compose.yml config -q && (make dev-api &) && sleep 10 && curl -sf 127.0.0.1:8001/v1/healthz`

### [ ] T-07 Synthetic receipt generator — CLAUDE
Workspace: BACKEND | Depends: T-01 | Refs: PRD §10 Evaluation plan
Deliver: `data/generator/` producing 200 receipts (cab, flight, hotel, meal, fuel, toll, broadband) as PNG and PDF
from HTML templates with randomised vendors, layouts, blur, rotation, folds; tampered variants (edited total,
edited date, re-saved PDF with editor Producer, screenshot frame, exact and near duplicates); `labels.csv`
with ground truth per field and tamper type. Only synthetic GSTINs that pass SPEC §5 checksum.
Done when: `python -m data.generator --n 200` writes files + labels; a test checks label/file consistency.
Verify: `uv run --project eval python -m data.generator --n 20 --out /tmp/gen && test -f /tmp/gen/labels.csv`

## Phase 1 — Extraction

### [ ] T-08 Receipt contract and validators (Python) — CLAUDE
Workspace: BACKEND | Depends: T-02 | Refs: SPEC §5, contracts/receipt.schema.json, contracts/test-vectors
Deliver: `schemas/receipt.py` (Pydantic mirror of the JSON schema), `services/validators.py`
(gstin, tax math, date sanity, amount normaliser, vendor canonicaliser).
Done when: all vectors in contracts/test-vectors pass; receipt_example.json validates.
Verify: `cd backend && uv run pytest -q tests/test_validators.py`

### [ ] T-09 LLM gateway client and stub mode — CLAUDE
Workspace: BACKEND | Depends: T-04 | Refs: PRD §13, SPEC §6, gateway/litellm.config.yaml
Deliver: `llm/gateway.py` (OpenAI client → LITELLM_URL, alias in, JSON out, schema validation, one repair retry,
timeouts per alias, llm_calls row per call), stub mode reading `tests/fixtures/llm/<alias>/`, prompt loader
(`llm/prompts/extract_text_v1.md`, `extract_image_v1.md`).
Also: no-LLM degraded mode from SPEC §6 (needs_confirmation extraction, template agent replies, chip-only re-ask), healthz `llm: degraded`.
Done when: stub-mode tests cover success, invalid JSON then repair, primary→fallback model, both fail → degraded mode.
Verify: `cd backend && LLM_MODE=stub uv run --env-file ../.env.dev pytest -q tests/test_gateway.py`

### [ ] T-10 Documents API and Tier C extraction — CLAUDE
Workspace: BACKEND | Depends: T-05, T-08, T-09 | Refs: SPEC §3 POST /v1/documents, PRD §22
Deliver: `api/documents.py`, `services/extraction.py`, `workers/extract_document.py`; idempotency by sha256;
creates/attaches draft claim and line; stores extracted_fields with source.
Done when: posting with `extraction` stores fields immediately; posting with only `ocr_text` queues a job that fills fields in stub mode; repeat sha256 returns 200 with same id.
Verify: `cd backend && LLM_MODE=stub uv run pytest -q tests/test_documents.py`

### [ ] T-11 Evaluation harness — CLAUDE
Workspace: BACKEND | Depends: T-07, T-09 | Refs: PRD §3 metrics, §10 Evaluation plan
Deliver: `eval/run_eval.py` (per alias: field exact match, category accuracy, latency p50/p95, failure rate;
writes `eval/results/<date>_<alias>.md` and `.json`).
Done when: runs in stub mode end to end and produces a results table.
Verify: `LLM_MODE=stub uv run --project eval python eval/run_eval.py --alias kh-extract-text --limit 10`

## Phase 2 — Checks

### [ ] T-12 Policy engine — CLAUDE
Workspace: BACKEND | Depends: T-08 | Refs: PRD §8, data/seed/policy_v1.json
Deliver: `services/policy.py` (JsonLogic evaluator, line context builder, city tier lookup, caps, Flag output with rule_id, remedies, policy_version).
Done when: each rule has a passing and a breaching test case.
Verify: `cd backend && uv run pytest -q tests/test_policy.py`

### [ ] T-13 Entitlements and reservations — CLAUDE
Workspace: BACKEND | Depends: T-05, T-12 | Refs: PRD §9, SPEC §5 Entitlement, PRD §22 sketch
Deliver: `services/entitlement.py`, `services/erp_client.py`, `api/entitlements.py`, refresh job.
Done when: tests cover available, nearly_used, partly_covered, exhausted (Arjun broadband), not_entitled, unknown,
period by expense date, two concurrent drafts cannot reserve the same balance, release on return.
Verify: `cd backend && uv run pytest -q tests/test_entitlements.py`

### [ ] T-14 Duplicate detection — CLAUDE
Workspace: BACKEND | Depends: T-10 | Refs: SPEC §5 Duplicates
Deliver: `services/duplicates.py` (sha256, pHash Hamming, fuzzy key).
Done when: generator duplicate pairs are all flagged with correct severity; unrelated receipts are not.
Verify: `cd backend && uv run pytest -q tests/test_duplicates.py`

### [ ] T-15 Forensics service and trust score — CLAUDE
Workspace: BACKEND | Depends: T-06, T-07 | Refs: PRD §11, SPEC §5 Trust score
Deliver: `forensics/app` endpoints `/analyze/image` (ELA hotspot, pHash, recapture heuristic) and `/analyze/pdf`
(Producer/Creator, ModDate vs CreationDate, incremental updates, font mix); `backend/services/trust.py` combining signals.
Done when: tampered set recall ≥ 0.8 with false-positive rate ≤ 0.1 on generator output (report numbers).
Verify: `cd forensics && uv run pytest -q && cd ../backend && uv run pytest -q tests/test_trust.py`

## Phase 3 — Claims and agent

### [ ] T-16 Claim state machine and claims API — CLAUDE
Workspace: BACKEND | Depends: T-12, T-13, T-14 | Refs: SPEC §3–4, PRD §15
Deliver: `services/claim_state.py`, `services/claims.py`, `api/claims.py` (draft list, validate, submit), audit events, grouping (SPEC §5).
Done when: every allowed transition works; every other raises ILLEGAL_TRANSITION; validate sets needs_info/ready correctly.
Verify: `cd backend && uv run pytest -q tests/test_claims.py tests/test_state_machine.py`

### [ ] T-17 Question planner — CLAUDE
Workspace: BACKEND | Depends: T-16 | Refs: PRD §7, SPEC §5 Question rule
Deliver: `agent/question_planner.py` + tests for each row of the PRD §7 table.
Done when: 10-receipt scenario fixture yields ≤ 2 questions.
Verify: `cd backend && uv run pytest -q tests/test_question_planner.py`

### [ ] T-18 Agent orchestrator and tools — CLAUDE
Workspace: BACKEND | Depends: T-09, T-17 | Refs: PRD §15 Agent tools, PRD §22 sketch
Deliver: `agent/orchestrator.py`, `agent/tools.py` (all tools listed in PRD §15), `agent/prompts/agent_v1.md`,
`api/agent.py`, template-only fallback when kh-agent is unavailable.
Done when: stub fixtures drive a full conversation to `ready`; tool results, not the LLM, set all amounts.
Verify: `cd backend && LLM_MODE=stub uv run pytest -q tests/test_agent.py`

### [ ] T-19 Submit, ERP sync and approvals — CLAUDE
Workspace: BACKEND | Depends: T-16, T-03 | Refs: SPEC §3–4
Deliver: `workers/submit_to_erp.py`, status polling job, `api/approvals.py`, `services/storage.py` (Storage interface + LocalStorage) saving originals on submit.
Done when: submit → in_review → approved → paid via mock ERP; return reopens as draft and releases reservations.
Verify: `cd backend && uv run --env-file ../.env.dev pytest -q tests/test_submit_flow.py` (mock ERP from infra-up)

## Phase 4 — Android

### [ ] T-20 Android scaffold — CLAUDE
Workspace: APP | Depends: T-01 | Refs: PRD §21, android/CLAUDE.md
Deliver: Gradle project (version catalog), Compose theme, navigation, Hilt, Room DB v1 with entities from PRD §21,
Gradle task copying contracts/test-vectors and contracts/prompts into app resources, product flavors `mock`, `dev`, `demo`
with API_BASE_URL per SPEC §1b and per-flavor network_security_config, `.github/workflows/android.yml` (paths: android/**, contracts/**).
Verify: `cd android && ./gradlew :app:assembleMockDebug :app:testMockDebugUnitTest`

### [ ] T-21 Capture, ingest, secure storage — HUMAN-VERIFY
Workspace: APP | Depends: T-20 | Refs: PRD §5 Capture channels, §21
Deliver: CaptureCoordinator, IngestDocumentsUseCase, SecureFileStore (Tink AEAD with Android Keystore), share-sheet intent filters.
Verify: unit tests with fake URIs pass; HUMAN: share a PDF from another app on a phone and see it in the thread.

### [ ] T-22 Quality gate and OCR — HUMAN-VERIFY
Workspace: APP | Depends: T-21 | Refs: SPEC §5 Quality gate
Deliver: QualityGate (pure Kotlin on bitmaps, unit-tested with fixture images), OcrEngine, PdfTextExtractor.
Verify: `./gradlew :app:testDebugUnitTest`; HUMAN: blurred photo prompts a retake on device.

### [ ] T-23 Device tiers and extractors — HUMAN-VERIFY
Workspace: APP | Depends: T-22 | Refs: PRD §10 Device tiering, SPEC §5 Device tier
Deliver: DeviceTierResolver, ThermalGuard, ReceiptExtractor + GeminiNanoExtractor, LiteRtLmExtractor, ServerExtractor,
ExtractionPromptBuilder (same prompt text as backend extract_text_v1), ReceiptJsonParser, ExtractionWorker.
Verify: unit tests with fake extractors; HUMAN: run the benchmark module on a phone, record tier and latency.

### [ ] T-24 Validators and trust signals (Kotlin) — CLAUDE
Workspace: APP | Depends: T-20 | Refs: SPEC §5
Deliver: GstinValidator, TaxMathValidator, DateSanityValidator, AmountNormalizer, ExifInspector, PdfMetadataInspector, TrustSignalCollector.
Done when: same test vectors as Python pass.
Verify: `cd android && ./gradlew :app:testDebugUnitTest --tests "*Validator*"`

### [ ] T-25 Network, sync and outbox — CLAUDE
Workspace: APP | Depends: T-20, T-00 | Refs: SPEC §1b, §3, contracts/openapi.yaml
Deliver: KharchaApi (Retrofit), AuthInterceptor, DTOs matching SPEC §3, SyncWorker, OutboxEntity processing, EntitlementRefreshWorker.
Verify: MockWebServer tests for each endpoint and offline replay; mock flavor against `./scripts/mock-api.sh`.
Integration check (after BACKEND T-10): dev flavor (localhost:8001 through `./scripts/tunnel.sh`) posts a document and sees it in GET /v1/claims/draft.

### [ ] T-26 Chat thread UI — HUMAN-VERIFY
Workspace: APP | Depends: T-23, T-25 | Refs: PRD §5 wireframes 1 and 3, principles table
Deliver: ChatScreen, ChatViewModel, ReceiptCard states, QuestionChips, needs-you counter; previews for each state.
Verify: Compose UI tests; HUMAN: drop 10 receipts on a phone.

### [ ] T-27 Review, entitlements and submit UI — HUMAN-VERIFY
Workspace: APP | Depends: T-26 | Refs: PRD §5 wireframes 2 and 4, PRD §9 states
Deliver: ReviewScreen (trip groups, flags, entitlement strip), SubmitScreen, status updates.
Verify: Compose UI tests against mock examples; HUMAN (after BACKEND T-13, dev flavor): Arjun sees broadband "Exhausted" with reset date.

## Phase 5 — Console, deploy, polish

### [ ] T-28 Approver console — CLAUDE
Workspace: APP | Depends: T-00 | Refs: PRD §6 CLM-3
Deliver: `console/` React + Vite + TS (dev against Prism mock, then the tunnel): login as approver, claim list, claim detail with flags and evidence, approve/return/reject.
Verify: `cd console && npm ci && npm run build && npm test`

### [ ] T-29 Deployment files — CLAUDE
Workspace: BACKEND | Depends: T-06 | Refs: PRD §24–26, deploy/, gateway/
Deliver: finalise deploy/server/{docker-compose.yml,nginx/kharcha.conf,initdb/} (host nginx, no Caddy), `deploy/scripts/{bootstrap_server.sh,deploy.sh,backup.sh,llm_smoke.sh}`,
`gateway/litellm.test.yaml` (stub). Do NOT run deploy.sh, touch /opt/kharcha, /etc/nginx or Guacamole.
Verify: `docker compose --env-file .env.example -f deploy/server/docker-compose.yml config -q && shellcheck deploy/scripts/*.sh scripts/*.sh`

### [ ] T-30 CI/CD workflows — CLAUDE
Workspace: BACKEND | Depends: T-02, T-29 | Refs: PRD §27
Deliver: `.github/workflows/{backend,eval}.yml` with path filters (backend/**, forensics/**, mock-erp/**, gateway/**, contracts/**); android.yml comes from T-20.
No deploy workflow: the hosted stack is built on the VM by `make deploy` (HUMAN).
Verify: `actionlint` passes; backend and android workflows green on a PR.

### [ ] T-31 End-to-end demo script — HUMAN-VERIFY
Workspace: BOTH | Depends: T-19, T-27, T-28 | Refs: PRD §17 demo storyline
Deliver: BACKEND: `data/demo/` receipt set for the storyline, `scripts/demo_reset.sh` (resets DB + mock ERP scenario), APP: Maestro flow `android/maestro/demo.yaml`.
Verify: HUMAN: full storyline in under 4 minutes on the hosted stack (demo flavor, https://$DOMAIN).

### [ ] T-32 Documentation and metrics — CLAUDE
Workspace: BACKEND | Depends: T-11, T-31 | Refs: PRD §3
Deliver: README setup ≤ 15 minutes; `docs/RESULTS.md` built from eval results and llm_calls; update PRD §3 targets vs actuals table in docs/RESULTS.md.
Verify: a fresh clone following docs/workspaces/SETUP.md reaches a green `127.0.0.1:8001/v1/healthz` and a green `https://$DOMAIN/v1/healthz`.

---
## HUMAN tasks (Claude Code prepares, you execute)
- [ ] H-01 Oracle Cloud: VCN, security rules (22 from your IP, 80/443 public), one VM kh-core (A1.Flex 2 OCPU / 12 GB), run `deploy/scripts/bootstrap_server.sh` (PRD §24). Before T-00.
- [ ] H-02 NVIDIA key: join the NVIDIA Developer Program, create an `nvapi-` key on build.nvidia.com → `/opt/kharcha/.env` (PRD §26). No other provider.
- [ ] H-03 DNS + nginx: DuckDNS (or similar) subdomain → kh-core public IP; set DOMAIN in `/opt/kharcha/.env`; install deploy/server/nginx/kharcha.conf and run `sudo certbot --nginx -d <subdomain>` (steps in the file header).
- [ ] H-04 GitHub: private repo, branch protection on main, kh-core SSH key added for clone/push.
- [ ] H-05 NVIDIA model check: open each model page in gateway/litellm.config.yaml, confirm the id and free endpoint, then `make llm-smoke` (after T-06).
- [ ] H-06 Test phone(s): enable developer mode; check GenAI feature availability; run benchmark (T-23).
- [ ] H-08 Claude Code on kh-core: log in, dev checkout ~/kharcha + .env.dev + CLAUDE.local.md, release checkout /opt/kharcha + .env, `make infra-up` (SETUP.md §2). Before T-00.
- [ ] H-09 Laptop: Android Studio, Node.js, Claude Code, clone, copy CLAUDE.local.APP.md, SSH config, test mock and tunnel (SETUP.md §3–4). Before T-20.
- [ ] H-07 First deploy: tag `v0.1.0`, `make deploy REF=v0.1.0` on kh-core, seed the hosted DB, smoke test `https://$DOMAIN/v1/healthz`.
