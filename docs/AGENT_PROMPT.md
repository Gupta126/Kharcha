# Standard task protocol for Claude Code (BACKEND workspace), v2

Follow CLAUDE.md, CLAUDE.local.md and backend/CLAUDE.md, plus everything below.

## Hard rules (breaking any of these means the task has failed)
- Environment problems are mine. On: connection refused, auth/password failed, permission denied,
  command not found, missing env variable, port in use: STOP and report the exact command and error.
- Never read or edit .env, .env.dev, .env.example, .env.dev.example, /opt/kharcha or /etc.
  If a new setting is needed: name it, give its dev value, and ask me to add it.
- Never hardcode passwords, credentialed URLs, API keys or machine paths. Use env vars and Path(__file__).
- No scratch or debug files, no *.bak copies, no print("DEBUG") or raise Exception("DEBUG").
- Edit files only with the Edit tool (never sed -i, awk or shell redirection).
- Dependencies: only well-known packages the task needs, listed in the plan with a reason.
  `uv add` for runtime, `uv add --dev` for tools. Python 3.12 only (no 3.13+ features; UUIDv7 from uuid6).
  Packages are discovered under app* only.
- Services that run in Docker install from pyproject.toml (`pip install .`); any change to a service must
  pass a docker build plus a short docker run check on a spare 127.0.0.1 port.
- Before committing Python changes: `uv run ruff format` and `uv run ruff check .` must be clean.
- Never change Verify commands or the approved acceptance script; never weaken, skip or delete tests.
- Touch only files needed for the task's Deliver list (plus uv.lock, docs/TASKS.md, docs/progress/, scripts/accept/).
- Earlier tasks marked [x] are not proof: check that what you build on actually exists and works.

## Progress file (so work survives a stopped session)
- At the start create docs/progress/<task-id>.md from docs/progress/TEMPLATE.md.
- After EVERY step: update Status, the checklist, "Last done" and "Next step", then
  `git add -A && git commit -m "wip(<task-id>): <step>" && git push -u origin <branch>`.
- If docs/progress/<task-id>.md already exists, this is a RESUME: read it, check `git log -5` and
  `git status`, run the acceptance script to see where things stand, and continue from "Next step".
  Do not redo finished steps.

## Flow
1. Sync: clean tree, main, pull (on resume: check out the existing branch instead).
2. Branch be/<task-id>-<topic>; create the progress file.
3. Read the task card, the PRD sections it references (docs/PRD.md only, never the PDF), SPEC, contracts/
   and the existing code it builds on. Check prerequisites (services up, earlier work really present).
4. Write scripts/accept/<task-id>.sh: a bash script (set -euo pipefail) that checks EVERY Deliver item and
   every "Done when" line concretely: files exist, endpoints return the expected JSON (curl + python
   assertions), tests pass with a minimum count, docker build/run for services, ./scripts/check_hygiene.sh.
   It prints one PASS or FAIL line per check and exits non-zero on any FAIL.
5. CHECKPOINT A: show the plan (files, functions, tests, dependencies with reasons) AND the acceptance
   script. Wait for my OK. After approval the script is frozen.
6. Build in small steps; after each: run the relevant tests, update the progress file, wip commit + push.
7. Run scripts/accept/<task-id>.sh. Max 3 fix attempts per failing check, then stop and report.
8. CHECKPOINT B, evidence: the full acceptance script output, plus a table mapping each Deliver item to the
   file/function and the check that proves it, plus `git diff main --stat`. Wait for my OK.
9. Tick [x] in docs/TASKS.md; set Status DONE in the progress file; commit
   "<type>(<scope>): <task-id> <title>"; push; gh pr create (title "<task-id>: <title>").
10. Unless I said "review gate": gh pr merge --squash --delete-branch, then main, pull, confirm [x].
11. Report in 5 bullets max: built, acceptance result, PR URL, HUMAN steps for me, anything uncertain.

Stuck rule: more than about 30 minutes or 3 failed attempts on one problem means stop, update the progress
file with what works, what fails and the exact error, push, and summarise for me.
