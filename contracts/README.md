# contracts/ — the only shared surface between the two workspaces
| File | Used by |
|---|---|
| openapi.yaml | backend implements it (contract test); app generates/handwrites DTOs from it; Prism serves it as a mock |
| receipt.schema.json | phone extractors, backend extraction, every LLM provider |
| test-vectors/*.json | Python and Kotlin validator tests |
| prompts/*.md | identical extraction prompt on phone (Tier A/B) and server (Tier C) |
Owner: BACKEND workspace. APP workspace requests changes in docs/CONTRACT_REQUESTS.md.
Every change: branch `contract/<topic>`, bump VERSION + CHANGELOG, merge before dependent app/backend work.
