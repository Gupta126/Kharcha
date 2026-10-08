# This machine is the APP workspace
@docs/workspaces/APP.md
- Only work on tasks marked `Workspace: APP`. If asked for anything else, say it belongs to the BACKEND workspace.
- Never edit contracts/; propose changes in docs/CONTRACT_REQUESTS.md.
- Default build flavor: mock. Use dev only when the tunnel is up (curl -s localhost:8001/v1/healthz). demo talks to https://$DOMAIN.
