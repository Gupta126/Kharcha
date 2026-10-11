#!/usr/bin/env bash
# Calls each gateway alias once with a tiny prompt. Reads LITELLM_MASTER_KEY from .env.dev.
set -euo pipefail
cd "$(dirname "$0")/../.."
KEY=$(grep '^LITELLM_MASTER_KEY=' .env.dev | cut -d= -f2)
for alias in kh-extract-text kh-agent kh-parse kh-extract-text-fb kh-agent-fb; do
  printf '%-22s ' "$alias"
  body=$(jq -nc --arg m "$alias" \
    '{model:$m, max_tokens:300, messages:[{role:"user", content:"Reply with OK"}]}')
  curl -s -m 30 http://127.0.0.1:4000/v1/chat/completions \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$body" \
    | jq -r '.choices[0].message.content // .error.message' | head -c 300
  echo
done
