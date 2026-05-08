# PRD: Minimal LLM-Powered Health Tracker

## Problem Statement

Users want a simple way to understand how their health metrics looked over a chosen period and get actionable guidance — without wading through dashboards, charts, or population comparisons. They need a conversational interface that can answer natural-language questions about their health data, validate what questions are actually answerable, and route each question to the right kind of response.

## Solution

A minimal web app where each user sees their raw health metrics on a summary screen and can ask natural-language questions via a chat box. Users can ask about any duration within the last month (e.g. "last week", "last 2 weeks", "last month"). A backend classifier validates and decomposes each request — including extracting the requested duration — a LangChain-based router selects the right prompt template per intent, and DeepSeek generates the response. All data is hardcoded in-memory for the hackathon MVP.

## User Stories

1. As a user, I want to see my raw health metrics for the last month on a single screen, so that I have context before asking questions.
2. As a user, I want to ask "How did I do last week?" and get a summary of my metrics vs. optimal targets for that period, so that I understand my overall performance.
3. As a user, I want to ask "What should I focus on over the next 2 weeks?" and get a prioritised action plan, so that I know what to improve.
4. As a user, I want to ask "How long did I sleep on average last month?" and get a direct answer, so that I can quickly look up a single metric.
5. As a user, I want to ask "How do my steps compare to optimal over the last 2 weeks?" and get a clear delta, so that I know how far off I am on a specific metric.
6. As a user, I want to ask "Break down all my metrics in detail for last month" and get a comprehensive review, so that I can do a deep review of my data.
7. As a user, I want to combine multiple questions in one message (e.g. "How did I do last week and what's my plan for next month?") and get all answers in a single response, so that I don't have to ask separately.
8. As a user, I want off-topic questions (e.g. "What's the weather?") to be rejected gracefully, so that the app stays focused.
9. As a user, I want out-of-range questions (e.g. "What were my metrics 6 months ago?") to be rejected with a clear explanation, so that I understand the app's limits.
10. As a user, I want questions about other users' data to be rejected, so that my data feels private.
11. As a user, I want missing metrics to be acknowledged explicitly ("You didn't log HRV for this period") rather than silently skipped, so that I know what's incomplete.
12. As a user, I want compound responses presented as clearly labelled sequential blocks, so that I can easily read each part of a multi-intent answer.
13. As a user, I want to switch between users via a URL param (`?user_id=1`), so that the demo can be shown for different users without a login flow.
14. As a developer, I want all user data and optimal targets stored in-memory as hardcoded Python structures, so that there is no database dependency for the hackathon.
15. As a developer, I want the classifier to return structured JSON including the requested duration, so that decomposition and routing logic is deterministic and testable.

## Implementation Decisions

### Data Model

The data store holds **30 days of daily metric entries** per user. Each day is a dict of the 6 metrics; any unlogged metric for that day is `None`. This allows the chain executor to slice any sub-window (1 week, 2 weeks, full month) before passing data to the LLM.

```
user_data[user_id] = [
  { "date": "2026-04-09", "sleep": 7.0, "steps": 9200, "resting_hr": 68, "water": 2.1, "workouts": 1, "hrv": 54 },
  { "date": "2026-04-10", "sleep": 6.5, "steps": 8100, "resting_hr": 71, "water": 1.9, "workouts": 0, "hrv": None },
  ...  # 30 entries total
]
```

The `GET /metrics/{user_id}` endpoint returns the full 30-day list. The classifier extracts a `duration_days` integer from the prompt (e.g. "last week" → `7`, "last 2 weeks" → `14`, "last month" → `30`). The chain executor slices the most recent `duration_days` entries before building the prompt context.

### Modules

**`data_store`**
- Hardcoded dict of users keyed by `user_id`
- Each user has a list of 30 daily metric dicts, each with a `date` key and 6 metric keys: `sleep` (hours), `steps`, `resting_hr` (bpm), `water` (litres), `workouts` (0 or 1 per day), `hrv` (ms)
- Separate static dict of expert-defined optimal targets for each metric (daily values)
- Interface: `get_user_metrics(user_id) -> list[dict]`, `get_optimal_targets() -> dict`
- `None` represents an unlogged metric for that day — never omit the key

**`classifier`**
- Single raw DeepSeek API call (not wrapped in LangChain)
- Input: `user_id`, `prompt`
- Output: `{valid: bool, reason: str | None, sub_requests: [{intent: str, focus_metric: str | None, duration_days: int}]}`
- `duration_days` is extracted from natural language: "last week" → `7`, "last 2 weeks" → `14`, "last month" → `30`; defaults to `30` if no duration is specified
- Valid intents: `performance_summary`, `next_period_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`
- Rejects: off-topic, cross-user, out-of-range (beyond 30 days) requests
- Returns `valid: false` with a human-readable `reason` for rejected requests

**`prompt_registry`**
- Dict mapping each intent string to a LangChain `ChatPromptTemplate`
- Each template receives: `user_metrics` (pre-sliced list), `optimal_targets`, `focus_metric` (optional), `duration_label` (human-readable string, e.g. "the last 7 days")
- 5 templates: `performance_summary`, `next_period_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`
- Null metric handling instruction baked into every template: acknowledge and skip missing values

**`chain_executor`**
- Receives sub-requests (each with `intent`, `focus_metric`, `duration_days`) and `user_id`
- Fetches full 30-day data from `data_store`, slices the most recent `duration_days` entries per sub-request
- Builds a `LLMChain` per sub-request by looking up the intent in `prompt_registry`
- DeepSeek accessed via `ChatOpenAI` with `base_url="https://api.deepseek.com"` (OpenAI-compatible)
- Runs all chains concurrently via LangChain `RunnableParallel`
- Returns ordered list of `{intent: str, label: str, response: str}`

**`response_assembler`**
- Takes ordered list of `{intent, label, response}`
- Formats into sequential labelled blocks: `"**{label}:**\n{response}"`
- Pure string logic, no LLM involvement

**`api`**
- FastAPI app
- `GET /metrics/{user_id}` — returns full 30-day list of daily metric dicts
- `POST /chat` — body: `{user_id, prompt}`, runs classifier → chain_executor → response_assembler, returns `{valid, reason, blocks: [{label, response}]}`

### API Contracts

`GET /metrics/{user_id}`
```
Response 200: [
  { "date": "2026-04-09", "sleep": 7.0, "steps": 9200, "resting_hr": 68, "water": 2.1, "workouts": 1, "hrv": 54 },
  ...
]
Response 404: { "error": "User not found" }
```

`POST /chat`
```
Request:  { "user_id": "1", "prompt": "How did I do last week?" }
Response 200 (valid): { "valid": true, "blocks": [{ "label": "Performance Summary (Last 7 Days)", "response": "..." }] }
Response 200 (invalid): { "valid": false, "reason": "That question is outside the scope of this app." }
```

### Architectural Decisions

- Classifier uses a raw DeepSeek call (not LangChain) to keep it independent and easily testable
- Duration extraction happens in the classifier — it returns `duration_days` as an integer so downstream modules never parse natural language
- Data slicing happens in `chain_executor`, not in `data_store` — keeps the store as a pure data source
- LangChain is used exclusively for prompt template management, chain construction, and parallel execution
- No session state — every `POST /chat` is stateless; full context (sliced metrics + targets) is injected per call
- `user_id` is passed as a URL param on the frontend (`?user_id=1`) and sent in the POST body
- No authentication, no database, no persistent storage

## Testing Decisions

A good test checks observable external behaviour only — what goes in and what comes out — never how the module achieves it internally.

**`data_store`** — unit test `get_user_metrics` for known user (returns 30-day list), unknown user, and user with null metrics on some days; test `get_optimal_targets` returns complete dict.

**`classifier`** — unit test with mocked DeepSeek HTTP responses: valid single intent with explicit duration ("last week" → `duration_days: 7`), valid compound intent (2+ sub-requests with different durations), no-duration prompt (defaults to `30`), off-topic rejection, out-of-range rejection, cross-user rejection.

**`response_assembler`** — unit test with a list of `{intent, label, response}` dicts; assert output string contains correct labels and ordering.

**`chain_executor`** — integration test (with mocked LangChain chains) that `RunnableParallel` is called with the correct number of chains, data is sliced to the correct `duration_days`, and results are returned in input order.

**`api`** — integration test both endpoints: `GET /metrics/{user_id}` for valid/invalid user; `POST /chat` for valid and rejected prompts (chain_executor mocked).

## Out of Scope

- User authentication and authorisation
- Persistent storage or database
- Historical data beyond the last 30 days
- Population-based analytics or user levels
- Trend analysis across periods longer than 30 days
- Frontend implementation (React, out of scope for this PRD)
- Push notifications or scheduled reports
- Any metric not in the defined set (sleep, steps, resting HR, water, workouts, HRV)

## Further Notes

- This is a hackathon MVP. All hardcoded data should be realistic and varied across users to make demos compelling.
- DeepSeek model: `deepseek-chat`. API key via environment variable `DEEPSEEK_API_KEY`.
- LangChain version: use `langchain` + `langchain-openai` packages.
- The classifier prompt should instruct DeepSeek to return only valid JSON with no preamble or markdown fences.
- Optimal targets are expert-defined daily constants, not computed from user data. They do not change at runtime.
- Duration mapping: "last week" → 7, "last 2 weeks" → 14, "last month" / no duration specified → 30. Any request for more than 30 days is out of range and should be rejected.
