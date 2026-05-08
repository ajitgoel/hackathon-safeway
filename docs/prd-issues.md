# GitHub Issues — Minimal LLM-Powered Health Tracker

---

## Issue 1: `data_store` module — hardcoded users, daily metrics, optimal targets

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement the `data_store` module with hardcoded in-memory user records and a static optimal targets dict. Each user has **30 daily metric entries** (one per day for the last month). Expose two functions: `get_user_metrics(user_id)` and `get_optimal_targets()`. Include at least 3 realistic, varied users — some days with null metrics to exercise the null-handling path.

### Acceptance criteria
- [ ] `get_user_metrics(user_id)` returns a list of 30 dicts, each with a `date` key and all 6 metric keys (`sleep`, `steps`, `resting_hr`, `water`, `workouts`, `hrv`), with `None` for any unlogged metric on that day
- [ ] `get_user_metrics(user_id)` raises `KeyError` for an unknown `user_id`
- [ ] `get_optimal_targets()` returns a complete dict with expert-defined daily target values for all 6 metrics
- [ ] At least 3 hardcoded users exist, with varied data and at least one `None` metric value across the set
- [ ] Returned lists are shallow copies — mutations do not affect internal state
- [ ] Unit tests pass for: known user (30 entries), unknown user, user with null metric on some days, optimal targets completeness

### Blocked by
None — can start immediately.

### User stories addressed
- User story 1 (see raw metrics)
- User story 11 (null metrics acknowledged)
- User story 13 (user switching via user_id)
- User story 14 (in-memory hardcoded data)

---

## Issue 2: `GET /metrics/{user_id}` endpoint — raw metrics API

**Parent PRD:** PRD-health-tracker.md

### What to build
Wire up a FastAPI `GET /metrics/{user_id}` endpoint that calls `get_user_metrics` from `data_store` and returns the full 30-day list of daily metric dicts as JSON. Return a 404 with `{"error": "User not found"}` for unknown users.

### Acceptance criteria
- [ ] `GET /metrics/1` returns 200 with a list of 30 daily metric dicts for a known user
- [ ] `GET /metrics/999` returns 404 with `{"error": "User not found"}`
- [ ] Null metric values are serialised as JSON `null` (not omitted)
- [ ] API integration test covers both cases

### Blocked by
- Blocked by Issue 1 (`data_store`)

### User stories addressed
- User story 1 (see raw metrics on summary screen)
- User story 13 (user_id via URL param)

---

## Issue 3: `classifier` module — validate, decompose, and extract duration from prompt

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement the `classifier` module as a single raw DeepSeek API call (not LangChain). It receives `user_id` and `prompt`, instructs DeepSeek to return only JSON (no preamble, no markdown), and parses the response into `{valid, reason, sub_requests: [{intent, focus_metric, duration_days}]}`.

Duration extraction rules (applied per sub-request):
- "last week" → `7`
- "last 2 weeks" → `14`
- "last month" or no duration specified → `30`
- Any request for more than 30 days → `valid: false` (out of range)

Valid intents: `performance_summary`, `next_period_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`.

### Acceptance criteria
- [ ] Valid single-intent prompt with explicit duration returns `{valid: true, sub_requests: [{..., duration_days: N}]}`
- [ ] Valid prompt with no duration specified returns `duration_days: 30` by default
- [ ] Valid compound prompt (e.g. "How did I do last week and what's my plan for next month?") returns `{valid: true, sub_requests: [two items, each with their own duration_days]}`
- [ ] Off-topic prompt returns `{valid: false, reason: "<human-readable explanation>"}`
- [ ] Out-of-range prompt (e.g. data older than 30 days) returns `{valid: false, reason: "..."}`
- [ ] Cross-user prompt returns `{valid: false, reason: "..."}`
- [ ] Unit tests pass for all cases above with mocked DeepSeek HTTP responses
- [ ] Classifier prompt instructs DeepSeek to return only valid JSON with no extra text

### Blocked by
- Blocked by Issue 1 (`data_store`)

### User stories addressed
- User story 8 (off-topic rejection)
- User story 9 (out-of-range rejection)
- User story 10 (cross-user rejection)
- User story 15 (structured JSON output including duration)

---

## Issue 4: `prompt_registry` — 5 LangChain ChatPromptTemplates

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement the `prompt_registry` as a dict mapping each intent string to a LangChain `ChatPromptTemplate`. Each template receives `user_metrics` (pre-sliced list of daily dicts), `optimal_targets`, `focus_metric` (optional), and `duration_label` (human-readable string, e.g. `"the last 7 days"`). All 5 intents must be covered. Every template must include an instruction to acknowledge and skip null metrics explicitly.

### Acceptance criteria
- [ ] Registry contains keys for all 5 intents: `performance_summary`, `next_period_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`
- [ ] Each template accepts `user_metrics`, `optimal_targets`, `focus_metric`, and `duration_label` as input variables
- [ ] Each template's system prompt explicitly instructs the LLM to acknowledge missing (null) metrics
- [ ] `single_metric_lookup` and `metric_comparison` templates use `focus_metric` meaningfully
- [ ] All templates reference `duration_label` so responses are scoped to the correct period
- [ ] Templates can be instantiated and formatted without error in a unit test

### Blocked by
- Blocked by Issue 1 (`data_store`)

### User stories addressed
- User story 2 (performance summary)
- User story 3 (next-period plan)
- User story 4 (single metric lookup)
- User story 5 (metric comparison)
- User story 6 (multi-metric deep dive)
- User story 11 (null metric acknowledgement)

---

## Issue 5: `chain_executor` — slice data by duration, build LangChain chains, run via RunnableParallel

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement `chain_executor` which takes a list of sub-requests (each with `intent`, `focus_metric`, `duration_days`) and `user_id`. For each sub-request it:
1. Fetches the full 30-day list from `data_store`
2. Slices the most recent `duration_days` entries
3. Builds a `duration_label` string (e.g. `"the last 7 days"`)
4. Looks up the intent in `prompt_registry` and builds a `LLMChain` bound to DeepSeek (via `ChatOpenAI` with `base_url="https://api.deepseek.com"`)

Runs all chains concurrently via `RunnableParallel`. Returns an ordered list of `{intent, label, response}` matching the input order.

### Acceptance criteria
- [ ] DeepSeek is configured via `ChatOpenAI` with `base_url="https://api.deepseek.com"` and `DEEPSEEK_API_KEY` from environment
- [ ] Data is sliced to the correct number of days per sub-request before being passed to the prompt
- [ ] `duration_label` is correctly derived from `duration_days` (7 → "the last 7 days", 14 → "the last 14 days", 30 → "the last 30 days")
- [ ] Single sub-request executes correctly and returns `{intent, label, response}`
- [ ] Multiple sub-requests run concurrently via `RunnableParallel` and results are returned in input order
- [ ] Unknown intent raises a clear error
- [ ] Integration test with mocked LangChain chains verifies correct slicing, correct number of chains, and ordering is preserved

### Blocked by
- Blocked by Issue 3 (`classifier`)
- Blocked by Issue 4 (`prompt_registry`)

### User stories addressed
- User story 7 (compound multi-intent questions answered in one response)
- User stories 2–6 (duration-scoped responses)

---

## Issue 6: `response_assembler` — format sequential labelled blocks

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement `response_assembler` as a pure function that takes an ordered list of `{intent, label, response}` dicts and returns a formatted string of sequential labelled blocks. No LLM involved — pure string logic only.

### Acceptance criteria
- [ ] Single block renders as `"**{label}:**\n{response}"`
- [ ] Multiple blocks are separated by a blank line and maintain input order
- [ ] Empty input list returns an empty string without error
- [ ] Unit tests cover: single block, multiple blocks, empty list

### Blocked by
None — can start immediately.

### User stories addressed
- User story 7 (compound questions answered in one response)
- User story 12 (sequential labelled blocks)

---

## Issue 7: `POST /chat` endpoint — wire classifier → executor → assembler

**Parent PRD:** PRD-health-tracker.md

### What to build
Implement the `POST /chat` FastAPI endpoint. It receives `{user_id, prompt}`, calls the classifier, and branches: if invalid returns `{valid: false, reason}` immediately; if valid, passes sub-requests (including `duration_days` per sub-request) to `chain_executor`, passes results to `response_assembler`, and returns `{valid: true, blocks: [{label, response}]}`. This is the full end-to-end pipeline wired together.

### Acceptance criteria
- [ ] Valid single-intent request with duration returns `{valid: true, blocks: [one block]}` scoped to the correct period
- [ ] Valid compound request returns `{valid: true, blocks: [multiple blocks in correct order]}`, each block scoped to its own duration
- [ ] Invalid request returns `{valid: false, reason: "..."}` without calling chain_executor
- [ ] Unknown `user_id` returns 404
- [ ] API integration test covers all 4 cases above (chain_executor mocked)
- [ ] `DEEPSEEK_API_KEY` missing from environment causes a clear startup error, not a runtime crash

### Blocked by
- Blocked by Issue 2 (`GET /metrics` endpoint)
- Blocked by Issue 3 (`classifier`)
- Blocked by Issue 5 (`chain_executor`)
- Blocked by Issue 6 (`response_assembler`)

### User stories addressed
- User stories 2–12 (full chat pipeline end-to-end)
