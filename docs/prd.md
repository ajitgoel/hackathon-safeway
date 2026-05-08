# PRD: Minimal LLM-Powered Weekly Health Tracker

## Problem Statement

Users want a simple way to understand how their health metrics looked last week and get actionable guidance — without wading through dashboards, charts, or population comparisons. They need a conversational interface that can answer natural-language questions about their health data, validate what questions are actually answerable, and route each question to the right kind of response.

## Solution

A minimal web app where each user sees their raw weekly health metrics on a summary screen and can ask natural-language questions via a chat box. A backend classifier validates and decomposes each request, a LangChain-based router selects the right prompt template per intent, and DeepSeek generates the response. All data is hardcoded in-memory for the hackathon MVP.

## User Stories

1. As a user, I want to see my raw health metrics for last week on a single screen, so that I have context before asking questions.
2. As a user, I want to ask "How did I do last week?" and get a summary of my metrics vs. optimal targets, so that I understand my overall performance.
3. As a user, I want to ask "What should I focus on next week?" and get a prioritised action plan, so that I know what to improve.
4. As a user, I want to ask "How long did I sleep on average?" and get a direct answer, so that I can quickly look up a single metric.
5. As a user, I want to ask "How do my steps compare to optimal?" and get a clear delta, so that I know how far off I am on a specific metric.
6. As a user, I want to ask "Break down all my metrics in detail" and get a comprehensive review, so that I can do a deep review of my week.
7. As a user, I want to combine multiple questions in one message (e.g. "How did I do last week and what's my plan?") and get all answers in a single response, so that I don't have to ask separately.
8. As a user, I want off-topic questions (e.g. "What's the weather?") to be rejected gracefully, so that the app stays focused.
9. As a user, I want out-of-range questions (e.g. "What were my metrics 6 months ago?") to be rejected with a clear explanation, so that I understand the app's limits.
10. As a user, I want questions about other users' data to be rejected, so that my data feels private.
11. As a user, I want missing metrics to be acknowledged explicitly ("You didn't log HRV last week") rather than silently skipped, so that I know what's incomplete.
12. As a user, I want compound responses presented as clearly labelled sequential blocks, so that I can easily read each part of a multi-intent answer.
13. As a user, I want to switch between users via a URL param (`?user_id=1`), so that the demo can be shown for different users without a login flow.
14. As a developer, I want all user data and optimal targets stored in-memory as hardcoded Python structures, so that there is no database dependency for the hackathon.
15. As a developer, I want the classifier to return structured JSON, so that decomposition and routing logic is deterministic and testable.

## Implementation Decisions

### Modules

**`data_store`**
- Hardcoded dict of users keyed by `user_id`
- Metrics per user: sleep (hours), steps, resting heart rate (bpm), water intake (litres), workouts (count), HRV (ms)
- Separate static dict of expert-defined optimal targets for each metric
- Interface: `get_user_metrics(user_id) -> dict`, `get_optimal_targets() -> dict`
- Null values are allowed and represented as `None`

**`classifier`**
- Single raw DeepSeek API call (not wrapped in LangChain)
- Input: `user_id`, `prompt`
- Output: `{valid: bool, reason: str | None, sub_requests: [{intent: str, focus_metric: str | None}]}`
- Valid intents: `performance_summary`, `next_week_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`
- Rejects: off-topic, cross-user, out-of-range requests
- Returns `valid: false` with a human-readable `reason` for rejected requests

**`prompt_registry`**
- Dict mapping each intent string to a LangChain `ChatPromptTemplate`
- Each template receives: `user_metrics`, `optimal_targets`, `focus_metric` (optional)
- 5 templates: `performance_summary`, `next_week_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`
- Null metric handling instruction baked into every template: acknowledge and skip missing values

**`chain_executor`**
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
- `GET /metrics/{user_id}` — calls `get_user_metrics`, returns raw dict
- `POST /chat` — body: `{user_id, prompt}`, runs classifier → chain_executor → response_assembler, returns `{valid, reason, blocks: [{label, response}]}`

### API Contracts

`GET /metrics/{user_id}`
```
Response 200: { "sleep": 6.5, "steps": 8200, "resting_hr": 72, "water": 1.8, "workouts": 3, "hrv": null }
Response 404: { "error": "User not found" }
```

`POST /chat`
```
Request:  { "user_id": "1", "prompt": "How did I do last week?" }
Response 200 (valid): { "valid": true, "blocks": [{ "label": "Performance Summary", "response": "..." }] }
Response 200 (invalid): { "valid": false, "reason": "That question is outside the scope of this app." }
```

### Architectural Decisions

- Classifier uses a raw DeepSeek call (not LangChain) to keep it independent and easily testable
- LangChain is used exclusively for prompt template management, chain construction, and parallel execution
- No session state — every `POST /chat` is stateless; full context (metrics + targets) is injected per call
- `user_id` is passed as a URL param on the frontend (`?user_id=1`) and sent in the POST body
- No authentication, no database, no persistent storage

## Testing Decisions

A good test checks observable external behaviour only — what goes in and what comes out — never how the module achieves it internally.

**`data_store`** — unit test `get_user_metrics` for known user, unknown user, and user with null metrics; test `get_optimal_targets` returns complete dict.

**`classifier`** — unit test with mocked DeepSeek HTTP responses: valid single intent, valid compound intent (2+ sub-requests), off-topic rejection, out-of-range rejection, cross-user rejection.

**`response_assembler`** — unit test with a list of `{intent, label, response}` dicts; assert output string contains correct labels and ordering.

**`chain_executor`** — integration test (with mocked LangChain chains) that `RunnableParallel` is called with the correct number of chains and returns results in input order.

**`api`** — integration test both endpoints: `GET /metrics/{user_id}` for valid/invalid user; `POST /chat` for valid and rejected prompts (chain_executor mocked).

## Out of Scope

- User authentication and authorisation
- Persistent storage or database
- Historical data beyond last week
- Population-based analytics or user levels
- Trend analysis across multiple weeks
- Frontend implementation (React, out of scope for this PRD)
- Push notifications or scheduled reports
- Any metric not in the defined set (sleep, steps, resting HR, water, workouts, HRV)

## Further Notes

- This is a hackathon MVP. All hardcoded data should be realistic and varied across users to make demos compelling.
- DeepSeek model: `deepseek-chat`. API key via environment variable `DEEPSEEK_API_KEY`.
- LangChain version: use `langchain` + `langchain-openai` packages.
- The classifier prompt should instruct DeepSeek to return only valid JSON with no preamble or markdown fences.
- Optimal targets are expert-defined constants, not computed from user data. They do not change at runtime.