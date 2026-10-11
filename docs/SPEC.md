# Kharcha — implementation spec (locked)

This file resolves every open choice in docs/PRD.pdf so the build can proceed without guessing.

> **VM-specific override:** kh-core already runs host **nginx** on 80/443 and **Apache Guacamole** in Docker.
> Kharcha therefore uses the existing nginx as its public entry (deploy/server/nginx/kharcha.conf + certbot) instead of
> the Caddy container shown in the PRD. Original files use local storage instead of the MinIO container in the PRD. Guacamole, its containers and the existing nginx sites must never be changed.
If this file and the PDF differ, this file wins. Change it only by explicit decision.

## 1. Locked decisions
| Topic | Decision |
|---|---|
| Currency | INR only. Amounts are integer paise. |
| Auth | Mock SSO: `POST /v1/auth/login {"email"}` for seeded users returns a JWT (HS256, `JWT_SECRET`, 12 h). Claims: `sub` (employee id), `role` (employee/approver/finance). No passwords. |
| IDs | UUIDv7 (python `uuid6` package; Kotlin generator in app). |
| Time zone | Store UTC (`timestamptz`); display Asia/Kolkata. Expense dates are local `date`. |
| Financial year | 1 April to 31 March. |
| Languages | English + Hindi OCR; UI English. |
| Max upload | 20 files per drop, 15 MB per file, PDF ≤ 10 pages. |
| Originals | Stay on device until submit; then uploaded and written under `STORAGE_DIR/<employee_id>/<sha256>.<ext>` via a `Storage` interface (`LocalStorage` now; an S3 implementation can be added later). No MinIO: its Docker Hub image was removed in 2026. |
| Queue names | `extract`, `forensics`, `agent`, `erp`; the dev runner prefixes them with `QUEUE_PREFIX=dev-`. |
| Ports | hosted api 127.0.0.1:8000 (behind host nginx 443), dev api 127.0.0.1:8001, mock-erp 8090, forensics 8085, litellm 4000, postgres 5432, redis 6379 — all bound to 127.0.0.1; only host nginx listens publicly. |
| Server | One Oracle VM, kh-core (A1.Flex arm64, 2 OCPU, 12 GB, Ubuntu 24.04): Claude Code development AND the hosted backend, alongside the existing Apache Guacamole. No micro VMs. |
| Edge | Existing host nginx; Kharcha gets its own server block for its subdomain; TLS by certbot. No Caddy. |
| Checkouts | `~/kharcha` = dev checkout (Claude Code works here); `/opt/kharcha` = release checkout (hosted stack, main or a tag). |
| Databases | `kharcha` (hosted), `kharcha_dev` (dev runner), `kharcha_test` (pytest) in the same Postgres; Redis DB 0 hosted, DB 1 dev; storage `/data/originals` (volume) / `~/kharcha-data/originals-dev`. |
| LLM | NVIDIA hosted models only (build.nvidia.com) through LiteLLM. No local model on the VM. |
| Prompt files | `backend/app/llm/prompts/<name>_v<N>.md` (extraction) and `backend/app/agent/prompts/<name>_v<N>.md` (agent). |

## 1b. Environments and base URLs
| Name | Where the API runs | Base URL seen by the app | LLM_MODE |
|---|---|---|---|
| mock | Prism on the laptop from contracts/openapi.yaml | emulator http://10.0.2.2:4010, USB phone http://localhost:4010 (adb reverse) | n/a |
| dev | dev runner on kh-core (`make dev-api`), 127.0.0.1:8001 | via scripts/tunnel.sh: emulator http://10.0.2.2:8001, phone http://localhost:8001 | stub (default) or live |
| demo | hosted stack on kh-core (PRD §24–25) | https://$DOMAIN | live |
Android build flavors `mock`, `dev`, `demo` set `API_BASE_URL` (host only; contract paths already start with /v1).
Contract compatibility: the app uses kotlinx.serialization with `ignoreUnknownKeys = true`; the backend contract test
compares FastAPI routes and response models against contracts/openapi.yaml and fails on any mismatch.

## 2. Error format
`{"error": {"code": "SNAKE_CASE", "message": "human readable", "details": {}}}`
Codes: `NOT_FOUND`, `VALIDATION_FAILED`, `ILLEGAL_TRANSITION`, `NOT_ENTITLED`, `DUPLICATE_DOCUMENT`,
`LLM_UNAVAILABLE`, `ERP_UNAVAILABLE`, `UNAUTHORIZED`, `FORBIDDEN`.

## 3. API contracts (all under /v1, JSON, bearer JWT except /auth/login and /healthz)
### POST /v1/documents
Request:
```json
{"sha256":"<64 hex>","mime":"image/jpeg","pages":1,
 "capture_source":"camera_scan|gallery|share|screenshot|pdf_download",
 "device_tier":"A|B|C","extraction": "<receipt.schema.json object or null>",
 "trust_signals":[{"name":"exif_inconsistent","failed":false}],
 "ocr_text":"<string, required when extraction is null>"}
```
Response 201: `{"document_id":"...","status":"extracted|queued|needs_confirmation","claim_id":"<draft id>","line_id":"..."}`
Same sha256 for the same employee → 200 with the existing document (idempotent), never a new row.

### GET /v1/claims/draft
Response: `{"claims":[ClaimView]}` where ClaimView =
```json
{"id":"...","title":"Pune client visit","status":"needs_info","total_paise":2212400,
 "lines":[{"id":"...","category":"hotel","expense_date":"2026-10-12","vendor":"...","amount_paise":980000,
           "claimable_paise":900000,"state":"partly_covered","flag_ids":["..."]}],
 "flags":[{"id":"...","type":"policy","severity":"amber","rule_id":"P-HTL-1","message":"...","evidence":{}}],
 "questions":[{"id":"...","field":"purpose","prompt":"...","options":["Client visit","Training"]}],
 "needs_you": 2}
```
### POST /v1/agent/messages
Request: `{"claim_id":"...","text":"optional free text","answer":{"question_id":"...","value":"..."}}`
Response: `{"reply":"...","claim":ClaimView}` (reply ≤ 3 sentences).
### POST /v1/claims/{id}/validate → `{"flags":[...],"ready":true|false}`
### POST /v1/claims/{id}/submit → 202 `{"status":"submitted","erp_ref":"ERP-2026-000123"}`; 409 `ILLEGAL_TRANSITION` unless status = ready.
### GET /v1/entitlements
`{"as_of":"<ts>","items":[{"category":"broadband","period":"fin_year","limit_paise":1500000,"paid_paise":1300000,
"pending_paise":0,"reserved_paise":99900,"available_paise":100100,"period_end":"2027-03-31"}]}`
### POST /v1/approvals/{claim_id} `{"action":"approve|return|reject","comment":"..."}` (role approver/finance)
### GET /v1/healthz → `{"db":"ok","redis":"ok","llm":"ok|degraded","erp":"ok"}`

## 4. Claim state machine
| From | To | Trigger |
|---|---|---|
| draft | needs_info | validate finds open required questions or red flags |
| needs_info | draft | all questions answered |
| draft | ready | validate: no open questions, no unresolved red flags |
| ready | draft | any line edited, added or removed |
| ready | submitted | submit (server re-checks entitlements first) |
| submitted | in_review | mock ERP status |
| in_review | approved / rejected / returned | approver action or ERP |
| returned | draft | automatic; reservations released |
| approved | paid | mock ERP payout; reservations → consumed; entitlement.paid += amount |
Any other transition → `ILLEGAL_TRANSITION`. Every transition writes an audit_events row.

## 5. Algorithms and thresholds
**GSTIN**: regex `^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$`; state code 01–38;
checksum: chars `0-9A-Z` map to 0..35; for i in 0..13: p = v * (1 if i even else 2); s += p // 36 + p % 36;
check = (36 − s % 36) % 36 must equal the 15th char. Vectors: contracts/test-vectors/gstin.json.
**Tax math**: if CGST and SGST present they must be equal (±1 paise) and IGST absent. taxable + taxes = total within
max(100 paise, 0.5% of total). Implied rate = taxes / taxable × 100 must be within 0.5 percentage points of a slab {0, 5, 12, 18, 28}; else amber.
Only one of CGST/SGST present → cgst_sgst_mismatch. Result codes: ok, cgst_sgst_mismatch, mixed_igst_cgst, total_mismatch, rate_not_slab.
Vectors: contracts/test-vectors/tax_math.json.
**Date sanity**: not in the future (device date + 1 day); older than policy P-AGE-1 (60 days) → red.
**Quality gate** (device): Laplacian variance < 100 → retake(blur); > 8% pixels with luminance ≥ 250 → retake(glare);
short edge < 800 px → retake(resolution).
**Confidence thresholds**: total, date 0.90; vendor, gstin 0.85; others 0.75. Below → question or cloud fallback.
**Duplicates**: same sha256 → red; pHash Hamming ≤ 6 → red if same employee, amber if another employee;
fuzzy key `lower(vendor_canonical)|expense_date|round(amount_paise/100)` with amount within ±1% → amber.
**Trust score**: start 100; subtract per failing signal: high 30, med 15, low 5; floor 0.
Bands ≥ 80 green, 50–79 amber, < 50 red. Never auto-reject.
Signals (weight): screenshot_source (low), exif_inconsistent (med), pdf_modified_after_creation (high),
pdf_editor_producer (high), tax_math_fail (high), gstin_invalid (high), recapture_suspected (med),
ela_hotspot_on_amount (med), template_mismatch (med), behavioural_pattern (low).
**Question rule**: ask(field) = required(field) AND (missing OR conf < threshold) AND NOT inferable(field).
priority = 3*blocks_submit + 2*policy_breach + 1*low_confidence; max 3 per turn; purpose asked once per claim.
**Entitlement**: available = limit − paid − pending(submitted, not paid) − reserved(other drafts).
States: available; nearly_used (≥ 80% used after this line); partly_covered (0 < available < amount);
exhausted (available = 0); not_entitled (no row for category); unknown (ERP unreachable, no cache).
claimable = min(amount, policy cap, category available, overall available).
**Grouping**: same trip if consecutive expense dates are ≤ 1 day apart AND city matches a flight/rail/hotel city
in that span; otherwise group by category per calendar month.
**Device tier**: thermal ≥ MODERATE → C; GenAI Prompt API available → A; RAM ≥ 6 GB and LiteRT model present → B; else C.

## 6. LLM gateway
Provider: NVIDIA build.nvidia.com only. Nemotron 3/3.5 are reasoning models: the gateway sends chat_template_kwargs.enable_thinking=false so replies are direct; never parse "thinking" text. Each alias has a primary and a fallback NVIDIA model (gateway/litellm.config.yaml).
Aliases and timeouts: kh-extract-image 20 s, kh-extract-text 20 s, kh-agent 8 s, kh-parse 5 s.
**No-LLM degraded mode** (both models failed, timed out, or 429 after retry):
- extraction: keep the phone's on-device result if Tier A/B; otherwise store OCR text and create questions asking the user
  to confirm total, date and vendor (prefilled from regex heuristics on the OCR text). Document status `needs_confirmation`.
- kh-agent: reply from templates using QuestionPlanner output (no free-text understanding).
- kh-parse: re-ask the same question with chips only.
- `/v1/healthz` reports `llm: degraded`; the app shows a small "assistant in basic mode" banner.
Dev and hosted share one NVIDIA key and its limits; keep `LLM_MODE=stub` in dev unless a task needs live calls. Tests use gateway stub mode: `LLM_MODE=stub` makes LLMGateway
return fixtures from backend/tests/fixtures/llm/<alias>/*.json (no network in tests, ever).
Every real call writes llm_calls(task, provider, model, latency_ms, tokens_in, tokens_out, success, failure).

## 7. Seed data
data/seed/employees.json (4 users with entitlements), data/seed/policy_v1.json.
Demo users: priya@kharcha.test (employee), arjun@kharcha.test (employee, broadband exhausted),
meera@kharcha.test (approver, manager of both), vikram@kharcha.test (finance).
