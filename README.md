# Kharcha — AI expense & reimbursement agent (starter kit)

Spec kit designed for Claude Code, split across two machines that share this repo through GitHub:

| Workspace | Machine | Owns |
|---|---|---|
| APP | your laptop (Android Studio) | android/, console/ |
| BACKEND | Oracle kh-core VM (arm64, 12 GB) — also hosts the backend | backend/, forensics/, mock-erp/, gateway/, eval/, data/, deploy/, contracts/ |

`contracts/` (OpenAPI, receipt schema, test vectors, shared prompt) is the only shared surface.
The app develops against a Prism mock of the contract until the backend is ready, then switches to the
real dev backend through an SSH tunnel. LLMs are NVIDIA hosted models only (build.nvidia.com); no model runs on the VM.
Claude Code is used as the terminal CLI on both machines.

## Start
1. Push this kit to a new private GitHub repo.
2. Follow docs/workspaces/SETUP.md for kh-core (§2) and the laptop (§3–4).
3. On each machine, open Claude Code in the repo root and say:
   "Read CLAUDE.md. Implement task T-xx from docs/TASKS.md only. Plan first, then build, then run its Verify commands and report."
   Order: docs/TASKS.md "Start here".

Specs: docs/PRD.pdf (PRD + development guide), docs/SPEC.md (locked rules), docs/TASKS.md (task board),
docs/schema.sql, contracts/. All data is synthetic. The finance system is mocked.
