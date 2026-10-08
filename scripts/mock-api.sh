#!/usr/bin/env bash
# Laptop: serve contracts/openapi.yaml as a mock API on :4010 (needs Node.js). -d = dynamic example data.
set -euo pipefail
cd "$(dirname "$0")/.."
exec npx -y @stoplight/prism-cli@5 mock contracts/openapi.yaml -p 4010 -h 0.0.0.0 -d
