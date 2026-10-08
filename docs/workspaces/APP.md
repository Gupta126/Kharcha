# APP workspace — your laptop (Claude Code terminal + Android SDK)

## Scope
Owns: `android/`, `console/`, `scripts/tunnel.sh`, `scripts/mock-api.sh`, `scripts/app-dev-connect.sh`.
Reads only: `contracts/`, `docs/`, `data/demo/`.
Never edits: `backend/`, `forensics/`, `mock-erp/`, `gateway/`, `eval/`, `deploy/`, `contracts/`.
Need a contract change? Add a row to docs/CONTRACT_REQUESTS.md and stop.

Claude Code runs in the terminal and builds with `./gradlew`. Android Studio is only needed for the
emulator, device logs and layout previews; you can also use `emulator` and `adb` from the SDK command line.

## Environments
| Build flavor | API_BASE_URL | Backend | When |
|---|---|---|---|
| `mock` | http://10.0.2.2:4010 (emulator) / http://localhost:4010 (USB phone, adb reverse) | Prism mock of contracts/openapi.yaml on the laptop | From day one |
| `dev` | http://10.0.2.2:8001 (emulator) / http://localhost:8001 (USB phone, adb reverse) | Dev runner on kh-core through the SSH tunnel | Integration |
| `demo` | https://$DOMAIN | Hosted stack on kh-core | Demo, HUMAN-VERIFY |
`mock` and `dev` allow cleartext only to localhost and 10.0.2.2; `demo` is HTTPS only.

## Daily start
```bash
git pull --rebase
./scripts/mock-api.sh            # flavor mock
./scripts/tunnel.sh              # flavor dev: forwards :8001 and :8090 from kh-core
./scripts/app-dev-connect.sh     # USB phone
claude
```
## Tasks
All tasks with `Workspace: APP` in docs/TASKS.md.
