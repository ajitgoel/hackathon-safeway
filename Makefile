.PHONY: run test test-file lint install deploy secrets logs status help

# ── Local development ────────────────────────────────────────────────────────

run:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-file:
	@test -n "$(f)" || (echo "Usage: make test-file f=tests/test_data_store.py" && exit 1)
	pytest $(f) -v

lint:
	ruff check . || true

install:
	pip install -r requirements.txt

# ── Docker ───────────────────────────────────────────────────────────────────

docker-build:
	docker build -t weekly-health-tracker .

docker-run:
	@test -n "$$DEEPSEEK_API_KEY" || (echo "Error: DEEPSEEK_API_KEY is not set" && exit 1)
	docker run --rm -p 8080:8080 -e DEEPSEEK_API_KEY=$$DEEPSEEK_API_KEY weekly-health-tracker

# ── Fly.io ───────────────────────────────────────────────────────────────────

deploy:
	fly deploy

secrets:
	@test -n "$(key)" || (echo "Usage: make secrets key=sk-your-key-here" && exit 1)
	fly secrets set DEEPSEEK_API_KEY=$(key)

logs:
	fly logs

status:
	fly status

# ── curl smoke tests (requires running server) ───────────────────────────────

BASE_URL ?= http://localhost:8000
USER_ID  ?= 1

smoke-metrics:
	curl -s $(BASE_URL)/metrics/$(USER_ID) | python3 -m json.tool

smoke-chat:
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do last week?"}' \
		| python3 -m json.tool

smoke-compound:
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do last week and what should I focus on next week?"}' \
		| python3 -m json.tool

smoke-invalid:
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "What is the weather today?"}' \
		| python3 -m json.tool

# ── Help ─────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Local development"
	@echo "    make install              Install dependencies from requirements.txt"
	@echo "    make run                  Start the API server with hot reload (port 8000)"
	@echo "    make test                 Run the full test suite"
	@echo "    make test-file f=<path>   Run a single test file"
	@echo "    make lint                 Run ruff linter"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-build         Build the Docker image"
	@echo "    make docker-run           Run the container (requires DEEPSEEK_API_KEY in env)"
	@echo ""
	@echo "  Fly.io"
	@echo "    make deploy               Deploy to Fly.io"
	@echo "    make secrets key=sk-...   Set DEEPSEEK_API_KEY as a Fly secret"
	@echo "    make logs                 Tail live logs"
	@echo "    make status               Show app status"
	@echo ""
	@echo "  Smoke tests (server must be running)"
	@echo "    make smoke-metrics        GET /metrics for USER_ID (default: 1)"
	@echo "    make smoke-chat           POST /chat — single intent"
	@echo "    make smoke-compound       POST /chat — compound intent"
	@echo "    make smoke-invalid        POST /chat — off-topic rejection"
	@echo "    Override user: make smoke-chat USER_ID=2"
	@echo ""
