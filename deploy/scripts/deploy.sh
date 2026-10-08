#!/usr/bin/env bash
# Deploy the hosted stack from the RELEASE checkout /opt/kharcha.
# HUMAN-run only (never by Claude Code unless asked).
# Usage: deploy/scripts/deploy.sh [git-ref]   (default: main; use a tag like v0.1.0 for the demo)
set -euo pipefail
REF=${1:-main}
REPO_URL=$(git -C "$(dirname "$0")/../.." remote get-url origin)
REL=/opt/kharcha

if [ ! -d "$REL/.git" ]; then
  git clone "$REPO_URL" "$REL"
fi
cd "$REL"
git fetch --tags origin
git checkout --quiet "$REF"
git pull --ff-only origin "$REF" 2>/dev/null || true   # no-op for tags
test -f .env || { echo "Missing $REL/.env (copy .env.example and fill it)"; exit 1; }

if [ -d console ] && [ -f console/package.json ]; then
  (cd console && npm ci && npm run build)
fi

DC=(docker compose --env-file .env -f deploy/server/docker-compose.yml)
"${DC[@]}" build
"${DC[@]}" up -d
"${DC[@]}" exec -T api alembic upgrade head
sleep 5
curl -fsS "https://$(grep '^DOMAIN=' .env | cut -d= -f2)/v1/healthz" && echo " <- healthz OK ($REF)"
