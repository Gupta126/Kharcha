# backend/ notes
- Layout: app/{api,core,db,models,schemas,services,agent,llm,workers,scripts}, tests/. See PRD §22.
- Routers are thin: validate -> call service -> return schema. No SQL or LLM calls in routers.
- Services take an AsyncSession; transactions are opened in the service layer.
- Error format: {"error": {"code": "SNAKE_CASE", "message": "...", "details": {}}} with proper HTTP status.
- Tests: pytest + httpx AsyncClient; DB tests use TEST_DATABASE_URL (kharcha_test on the shared Postgres) with a per-test transaction rollback.
- Settings must read QUEUE_PREFIX (dev runner uses dev-) and never default to the hosted database.
- LLM tests use the `stub` provider in gateway config (tests must not call real vendors).
