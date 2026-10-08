# BACKEND workspace — Oracle kh-core VM (Claude Code terminal over SSH)

## Scope
Owns: `backend/`, `forensics/`, `mock-erp/`, `gateway/`, `eval/`, `data/`, `deploy/`, `contracts/`.
Never edits: `android/`, `console/`.
Contract owner: changes to `contracts/` go on a `contract/<topic>` branch with VERSION + CHANGELOG bump.

## One VM, two roles
kh-core (VM.Standard.A1.Flex, arm64, 2 OCPU / 12 GB) is both the development machine and the backend host.
| | Dev (Claude Code) | Hosted (demo) |
|---|---|---|
| Checkout | `~/kharcha` (feature branches) | `/opt/kharcha` (main or a tag) |
| Started by | `make dev-api`, `make dev-worker` (host processes via uv) | `make deploy REF=...` (HUMAN) |
| API | 127.0.0.1:8001 (tunnel only) | host nginx https://$DOMAIN → 127.0.0.1:8000 |
| Data | `kharcha_dev`, Redis DB 1, `~/kharcha-data/originals-dev` | `kharcha`, Redis DB 0, volume `originals` |
| Env | `~/kharcha/.env.dev` | `/opt/kharcha/.env` |
Postgres, Redis, mock ERP, forensics and the LiteLLM gateway run once (hosted compose project `kharcha`)
and are shared by both roles through 127.0.0.1. Only the existing host nginx (80/443) is reachable from the internet;
it already serves Apache Guacamole and gets one extra server block for Kharcha. Do not touch Guacamole.

## LLM
NVIDIA build.nvidia.com models only, via LiteLLM on 127.0.0.1:4000 (gateway/litellm.config.yaml). No local model.
Dev and hosted share the same NVIDIA key and limits: keep `LLM_MODE=stub` in .env.dev unless a task needs live calls.

## Memory budget (12 GB)
| Process | Approx. |
|---|---|
| Apache Guacamole + host nginx (existing, not ours) | measure with `docker stats` |
| Hosted stack (api, worker, forensics, mock-erp, litellm, postgres, redis) | ~3.5 GB caps |
| Dev runner (uvicorn --reload + rq worker) | ~0.6 GB |
| Claude Code + uv/pytest runs | ~1.5–2 GB |
| OS + page cache | ~1–2 GB |
Fits with Guacamole if Guacamole stays under ~3 GB; 4 GB swap is the safety net. Check with `make status`.

## Daily start
```bash
ssh kh-core
tmux new -As kharcha          # window 1: claude | window 2: make dev-api | window 3: make dev-worker
cd ~/kharcha && git pull --rebase
claude
```
## Tasks
All tasks with `Workspace: BACKEND` in docs/TASKS.md.
