# Kharcha — AI expense & reimbursement agent

Monorepo for a hackathon prototype: Android app + Python backend + mock finance (ERP).
Turns a pile of receipts into a verified, policy-checked, submit-ready claim.
All data is synthetic. The finance system is mocked. Never use real receipts or real company data.

## Quick Start

### Prerequisites
- [uv](https://docs.astral.sh/uv/) (Python package installer)
- [Node.js](https://nodejs.org/) (for console)
- [Android Studio](https://developer.android.com/studio) (for Android app)
- [Claude Code](https://claude.ai/code) (recommended development tool)

### Backend Development
```bash
# Switch to backend directory
cd backend

# Synchronize dependencies
uv sync

# Run tests
uv run pytest -q

# Start development API
make dev-api

# Start development worker
make dev-worker
```

### Android App Development
```bash
# Switch to android directory
cd android

# Build the app
./gradlew :app:assembleMockDebug

# Run unit tests
./gradlew :app:testMockDebugUnitTest
```

### Console Development
```bash
# Switch to console directory
cd console

# Install dependencies
npm ci

# Run build
npm run build

# Run tests
npm test
```

### Available Commands
See the Makefile for all available commands:
- `make help` - List all commands
- `make contract-check` - Validate API contracts
- `make backend-test` - Run backend tests
- `make android-test` - Run Android tests
- `make eval` - Run evaluation harness

## Workspaces

This repository uses a two-workspace model:
- **APP Workspace**: Android app and console (laptop development)
- **BACKEND Workspace**: Python backend services (VM development)

See `docs/workspaces/` for detailed setup guides.

## Documentation
- Product requirements: `docs/PRD.md`
- Specifications: `docs/SPEC.md`
- Task breakdown: `docs/TASKS.md`
- API contracts: `contracts/openapi.yaml`
