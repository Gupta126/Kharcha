# This machine is the BACKEND workspace (Oracle kh-core, arm64)
@docs/workspaces/BACKEND.md
- Only work on tasks marked `Workspace: BACKEND`. android/ and console/ belong to the APP workspace.
- You own contracts/: change it only on a contract/ branch, bump contracts/VERSION and CHANGELOG, keep the contract test green.
- Default LLM_MODE=stub. Use live only when the task says so and keys are present in .env.
- This VM also runs the hosted demo from /opt/kharcha. Do not touch it; work only in ~/kharcha with .env.dev and port 8001.
- LLM calls go to NVIDIA via the gateway; they share one key with the hosted stack, so prefer stub mode.
