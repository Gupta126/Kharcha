# Standard task protocol for Claude Code (BACKEND workspace)

Follow CLAUDE.md, CLAUDE.local.md and backend/CLAUDE.md, plus everything below.

## Hard rules (breaking any of these means the task has failed)
- Environment problems are mine, not yours. If you see: connection refused, password/auth failed,
  permission denied, command not found, missing env variable, or a port in use, STOP immediately and
  report the exact command and error. Do not work around it, guess values, or hardcode anything.
- Never read or edit .env, .env.dev, .env.example, .env.dev.example, /opt/kharcha or /etc.
  If you need a new setting, name it, give its dev value, and ask me to add it.
- Never hardcode passwords, URLs with credentials, API keys or machine paths (/home/...). Read config
  from environment variables and paths from Path(__file__).
- No scratch or debug files, no *.bak or *.backup copies, no print("DEBUG") or raise Exception("DEBUG").
  Investigate with tests or commands, not new files.
- Change files only with your Edit tool, never with sed -i, awk or shell redirection.
- Dependencies: only well-known packages the task needs, listed in the plan with a reason; `uv add` for
  runtime, `uv add --dev` for tools. Python stays 3.12. Packages are discovered under app* only.
- Do not change the task's Verify commands, and do not weaken, skip, xfail or delete tests to make them pass.
- Touch only files in the task's Deliver list (plus uv.lock and docs/TASKS.md for the tick).

## Flow, with checkpoints where you STOP and wait for my "OK"
1. Sync: working tree clean, on main, pull. If not clean, stop and tell me.
2. Branch: be/<task-id>-<short-topic>.
3. Read: the task card, every PRD section it references (docs/PRD.md only, never the PDF), the SPEC
   sections, contracts/ if relevant, and the existing code it builds on. Check prerequisites (services
   running, earlier tasks [x]); if one is missing, stop and tell me.
4. CHECKPOINT A, plan: files to create or change, functions and classes, tests to write, new dependencies
   with reasons, and the exact Verify commands. Wait for OK.
5. Build in small steps; run the relevant tests after each step.
6. Verify: run every Verify command. Per failure, max 3 fix attempts; then stop and report the exact error.
7. Hygiene: git add -A, then ./scripts/check_hygiene.sh must print "hygiene: OK". Show `git status --short`.
8. CHECKPOINT B, evidence: paste the last lines of each Verify command's real output, the hygiene result,
   and `git diff --cached --stat`. Wait for OK.
9. Tick the task [x] in docs/TASKS.md, commit (conventional message with the task id), push -u,
   gh pr create (title "<task-id>: <title>", body = what changed and how verified).
10. Unless I said "review gate": gh pr merge --squash --delete-branch, switch to main, pull, confirm the [x].
11. Report in 5 bullets max: what was built, Verify results, PR URL, anything I must do (HUMAN steps),
    anything you were unsure about.

If you are about to spend more than about 30 minutes or 3 failed attempts on one problem, stop and
summarise: what works, what fails, the exact error, and what you would try next.
