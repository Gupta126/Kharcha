# Kharcha developer commands. Run `make help`.
# BACKEND workspace = dev checkout ~/kharcha on kh-core. Hosted stack = release checkout /opt/kharcha.
REL=/opt/kharcha
HOSTED=cd $(REL) && docker compose --env-file .env -f deploy/server/docker-compose.yml
SVC?=postgres redis minio
UVB=cd backend && uv run --env-file ../.env.dev
.PHONY: help infra-up status dev-api dev-worker migrate-dev seed-dev backend-test llm-smoke contract-check mock-api android-test eval deploy

help:            ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'
infra-up:        ## BACKEND: start shared services from the release checkout, e.g. make infra-up SVC="postgres redis minio mock-erp"
	cd $(REL) && git pull --ff-only
	$(HOSTED) up -d --build $(SVC)
status:          ## BACKEND: containers + memory
	docker compose -p kharcha ps; free -h
dev-api:         ## BACKEND: dev API on 127.0.0.1:8001 (kharcha_dev DB, LLM_MODE from .env.dev)
	$(UVB) uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
dev-worker:      ## BACKEND: dev worker on Redis DB 1, queues prefixed dev-
	$(UVB) rq worker --url redis://127.0.0.1:6379/1 dev-extract dev-forensics dev-agent dev-erp
migrate-dev:     ## BACKEND: alembic upgrade head on kharcha_dev
	$(UVB) alembic upgrade head
seed-dev:        ## BACKEND: load data/seed into kharcha_dev
	$(UVB) python -m app.scripts.seed --employees ../data/seed/employees.json --policy ../data/seed/policy_v1.json
backend-test:    ## BACKEND: ruff + mypy + pytest (kharcha_test DB, LLM stub)
	$(UVB) ruff check . && $(UVB) mypy app && LLM_MODE=stub $(UVB) pytest -q
	cd forensics && uv run pytest -q
	cd mock-erp && uv run pytest -q
llm-smoke:       ## BACKEND: one tiny call per gateway alias through LiteLLM (uses NVIDIA quota)
	./deploy/scripts/llm_smoke.sh
contract-check:  ## both: validate contracts/openapi.yaml and the receipt schema
	uvx --from openapi-spec-validator openapi-spec-validator contracts/openapi.yaml
	uvx --from check-jsonschema check-jsonschema --check-metaschema contracts/receipt.schema.json
mock-api:        ## APP: Prism mock of the contract on :4010
	./scripts/mock-api.sh
android-test:    ## APP: unit tests + lint (mock flavor)
	cd android && ./gradlew :app:testMockDebugUnitTest :app:lintMockDebug
eval:            ## BACKEND: evaluation against NVIDIA models (LLM_MODE=live)
	uv run --project eval --env-file .env.dev python eval/run_eval.py --alias all
deploy:          ## HUMAN ONLY: deploy hosted stack from /opt/kharcha. Usage: make deploy REF=v0.1.0
	./deploy/scripts/deploy.sh $(REF)
