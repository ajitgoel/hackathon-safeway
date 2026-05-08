.PHONY: run run-debug test test-file lint install docker-build docker-run deploy secrets logs status smoke-metrics smoke-chat smoke-compound smoke-invalid smoke-performance-summary smoke-performance-summary-2w smoke-performance-summary-month smoke-next-week-plan smoke-next-month-plan smoke-single-metric smoke-metric-comparison smoke-multi-metric-deep-dive smoke-off-topic smoke-out-of-range smoke-cross-user smoke-all help

# Load .env if it exists — exports all vars into the make environment
ifneq (,$(wildcard .env))
  include .env
  export
endif

# ── Local development ────────────────────────────────────────────────────────

run:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000

run-debug:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000 --log-level debug

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

# ── Chat smoke tests by intent ────────────────────────────────────────────────

# performance_summary — various durations
smoke-chat: smoke-performance-summary

smoke-performance-summary:
	@echo "\n── performance_summary (last week) ──────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do last week?"}' \
		| python3 -m json.tool

smoke-performance-summary-2w:
	@echo "\n── performance_summary (last 2 weeks) ───────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do over the last 2 weeks?"}' \
		| python3 -m json.tool

smoke-performance-summary-month:
	@echo "\n── performance_summary (last month) ─────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do last month?"}' \
		| python3 -m json.tool

# next_period_plan — various durations
smoke-next-week-plan:
	@echo "\n── next_period_plan (next week) ─────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "What should I focus on next week?"}' \
		| python3 -m json.tool

smoke-next-month-plan:
	@echo "\n── next_period_plan (next month) ────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "What should I focus on next month?"}' \
		| python3 -m json.tool

# single_metric_lookup — with explicit duration
smoke-single-metric:
	@echo "\n── single_metric_lookup (last 2 weeks) ──────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How long did I sleep on average over the last 2 weeks?"}' \
		| python3 -m json.tool

# metric_comparison — "How do my steps compare to optimal?"
smoke-metric-comparison:
	@echo "\n── metric_comparison ────────────────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How do my steps compare to the optimal target?"}' \
		| python3 -m json.tool

# multi_metric_deep_dive — "Break down all my metrics in detail"
smoke-multi-metric-deep-dive:
	@echo "\n── multi_metric_deep_dive ───────────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "Break down all my metrics in detail."}' \
		| python3 -m json.tool

# compound — multiple intents with different durations in one message
smoke-compound:
	@echo "\n── compound (performance_summary last week + next_period_plan next month) ──"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did I do last week and what should I focus on next month?"}' \
		| python3 -m json.tool

# rejection — off-topic question
smoke-invalid: smoke-off-topic

smoke-off-topic:
	@echo "\n── rejection: off-topic ─────────────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "What is the weather today?"}' \
		| python3 -m json.tool

# rejection — out-of-range (historical data)
smoke-out-of-range:
	@echo "\n── rejection: out-of-range ──────────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "What were my metrics 6 months ago?"}' \
		| python3 -m json.tool

# rejection — cross-user query
smoke-cross-user:
	@echo "\n── rejection: cross-user ────────────────────────────────────────"
	curl -s -X POST $(BASE_URL)/chat \
		-H "Content-Type: application/json" \
		-d '{"user_id": "$(USER_ID)", "prompt": "How did user 2 do last week?"}' \
		| python3 -m json.tool

# run all chat smoke tests in sequence
smoke-all: smoke-metrics smoke-performance-summary smoke-performance-summary-2w smoke-performance-summary-month smoke-next-week-plan smoke-next-month-plan smoke-single-metric smoke-metric-comparison smoke-multi-metric-deep-dive smoke-compound smoke-off-topic smoke-out-of-range smoke-cross-user

# ── Help ─────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Local development"
	@echo "    make install              Install dependencies from requirements.txt"
	@echo "    make run                  Start the API server with hot reload (port 8000)"
	@echo "    make run-debug            Same but with verbose logging"
	@echo "    make test                 Run the full test suite"
	@echo "    make test-file f=<path>   Run a single test file"
	@echo "    make lint                 Run ruff linter"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-build         Build the Docker image"
	@echo "    make docker-run           Run the container (reads DEEPSEEK_API_KEY from .env)"
	@echo ""
	@echo "  Fly.io"
	@echo "    make deploy               Deploy to Fly.io"
	@echo "    make secrets key=sk-...   Set DEEPSEEK_API_KEY as a Fly secret"
	@echo "    make logs                 Tail live logs"
	@echo "    make status               Show app status"
	@echo ""
	@echo "  Smoke tests (server must be running)"
	@echo "    make smoke-metrics                  GET /metrics for USER_ID (default: 1)"
	@echo "    make smoke-chat                     POST /chat — performance summary last week (default)"
	@echo "    make smoke-performance-summary      POST /chat — performance_summary, last week (7 days)"
	@echo "    make smoke-performance-summary-2w   POST /chat — performance_summary, last 2 weeks (14 days)"
	@echo "    make smoke-performance-summary-month POST /chat — performance_summary, last month (30 days)"
	@echo "    make smoke-next-week-plan           POST /chat — next_period_plan, next week"
	@echo "    make smoke-next-month-plan          POST /chat — next_period_plan, next month"
	@echo "    make smoke-single-metric            POST /chat — single_metric_lookup, last 2 weeks"
	@echo "    make smoke-metric-comparison        POST /chat — metric_comparison intent"
	@echo "    make smoke-multi-metric-deep-dive   POST /chat — multi_metric_deep_dive intent"
	@echo "    make smoke-compound                 POST /chat — compound: different durations per intent"
	@echo "    make smoke-off-topic                POST /chat — rejection: off-topic"
	@echo "    make smoke-out-of-range             POST /chat — rejection: historical data (>30 days)"
	@echo "    make smoke-cross-user               POST /chat — rejection: cross-user query"
	@echo "    make smoke-all                      Run all smoke tests in sequence"
	@echo "    Override user: make smoke-chat USER_ID=2"
	@echo ""
