#!/usr/bin/env bash
# Repo hygiene gate. Run before every commit: ./scripts/check_hygiene.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
fail=0
bad() { echo "FAIL: $*"; fail=1; }

# 1. secrets and private files
git ls-files | grep -E '(^|/)\.env(\.dev)?$|CLAUDE\.local\.md' && bad "env file or CLAUDE.local.md is tracked"
git diff --cached | grep -nE 'kharcha:[0-9a-f]{8,}@|nvapi-[A-Za-z0-9_-]{10,}|sk-[0-9a-f]{20,}' && bad "secret in staged changes"

# 2. debug leftovers in source
grep -rnE --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=node_modules --include='*.py' 'DEBUG:|breakpoint\(|import pdb|raise Exception\("DEBUG' \
  backend forensics mock-erp eval 2>/dev/null && bad "debug code left in source"

# 3. junk files (backups, scratch scripts)
git status --porcelain | awk '{print $2}' \
  | grep -E '\.(bak|backup|debug|orig)$|(^|/)(debug_|scratch_|tmp_)[^/]*\.py$' && bad "junk files present"

# 4. hardcoded machine paths
grep -rnE --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=node_modules --include='*.py' --include='*.ini' --include='*.toml' '/home/ubuntu|/Users/' \
  backend forensics mock-erp eval 2>/dev/null && bad "hardcoded machine paths"

# 5. Python version pin
for proj in backend forensics mock-erp eval; do
  [ -f "$proj/pyproject.toml" ] || continue
  { [ -f "$proj/.python-version" ] && grep -q '^3\.12' "$proj/.python-version"; } || bad "$proj not pinned to Python 3.12"
done

[ "$fail" -eq 0 ] && echo "hygiene: OK"
exit "$fail"
