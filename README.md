# Weekly Health Tracker

A minimal LLM-powered API that lets users query their 30-day health metrics via natural language. Built with FastAPI, LangChain, and DeepSeek.

## Prerequisites

- Python 3.10+
- A [DeepSeek API key](https://platform.deepseek.com/)

## Local setup

```bash
pip install -r requirements.txt
```

### Configure the API key

The app requires `DEEPSEEK_API_KEY` at startup. Set it in your shell before running:

```bash
export DEEPSEEK_API_KEY=sk-your-key-here
```

Or create a `.env` file (never commit this):

```
DEEPSEEK_API_KEY=sk-your-key-here
```

Then load it before starting:

```bash
set -a && source .env && set +a
```

### Run the server

```bash
uvicorn api:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run the tests

```bash
pytest
```

---

## API reference

Two base URLs are used in the examples below:

| Environment | Base URL |
|-------------|----------|
| Local | `http://localhost:8000` |
| Fly.io | `https://weekly-health-tracker.fly.dev` |

---

### `GET /metrics/{user_id}`

Returns 30 days of daily health metrics for a user, ordered oldest-first. Any metric the user did not log on a given day is returned as `null`.

**Local:**

```bash
curl http://localhost:8000/metrics/1
```

**Fly.io:**

```bash
curl https://weekly-health-tracker.fly.dev/metrics/1
```

```json
[
  {
    "date": "2026-04-09",
    "sleep": 7.0,
    "steps": 9200,
    "resting_hr": 68,
    "water": 2.1,
    "workouts": 1,
    "hrv": 54
  },
  {
    "date": "2026-04-10",
    "sleep": 6.5,
    "steps": 8100,
    "resting_hr": 71,
    "water": 1.9,
    "workouts": 0,
    "hrv": null
  }
]
```

*(30 entries total — truncated above for brevity)*

**Unknown user:**

```bash
curl https://weekly-health-tracker.fly.dev/metrics/999
```

```json
{
  "error": "User not found"
}
```

HTTP status: `404`

---

### `POST /chat`

Classifies a natural-language prompt, routes it to the appropriate LangChain prompt template(s), calls DeepSeek, and returns labelled response blocks. Each block label includes the duration it covers.

**Request body:**

```json
{
  "user_id": "1",
  "prompt": "How did I do last week?"
}
```

---

#### Performance summary — last week (7 days)

**Local:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last week?"}'
```

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last week?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary (Last 7 Days)",
      "response": "Here's how you did over the last 7 days:\n- Sleep: 6.8h avg (target 8h) — below target by 1.2h\n- Steps: 9,400 avg (target 10,000) — 600 short\n- Resting HR: 69 bpm avg (target 60 bpm) — above target\n- Water: 2.1L avg (target 2.5L) — below target\n- Workouts: logged on 4 of 7 days (target: daily)\n- HRV: not logged on some days this period\n\nOverall: a solid week with room to improve on sleep and hydration."
    }
  ]
}
```

---

#### Performance summary — last 2 weeks (14 days)

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do over the last 2 weeks?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary (Last 14 Days)",
      "response": "Here's your performance over the last 14 days:\n- Sleep: 7.0h avg (target 8h) — 1h below target\n- Steps: 9,200 avg (target 10,000) — close but not quite\n- Resting HR: 68 bpm avg (target 60 bpm) — above target\n- Water: 2.1L avg (target 2.5L) — below target\n- Workouts: consistent effort across the fortnight\n- HRV: not logged on several days\n\nOverall: a consistent two weeks — sleep and hydration are the main areas to address."
    }
  ]
}
```

---

#### Performance summary — last month (30 days)

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last month?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary (Last 30 Days)",
      "response": "Monthly review:\n- Sleep: 7.1h avg (target 8h) — consistently below target\n- Steps: 9,300 avg (target 10,000) — nearly there\n- Resting HR: 68 bpm avg (target 60 bpm) — elevated\n- Water: 2.1L avg (target 2.5L) — below target\n- Workouts: good frequency overall\n- HRV: incomplete logging — data missing on multiple days\n\nOverall: a decent month. Prioritise sleep and hydration to see the biggest gains."
    }
  ]
}
```

---

#### Next period plan — next week

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What should I focus on next week?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Next Period Plan (Last 30 Days)",
      "response": "Top priorities for next week:\n1. Sleep — aim for 8h by setting a consistent bedtime 30 minutes earlier\n2. Hydration — carry a 500ml bottle and refill 5x daily to hit 2.5L\n3. Resting HR — your elevated HR suggests recovery needs attention; add a rest day\n4. HRV — start logging daily for better trend visibility"
    }
  ]
}
```

---

#### Next period plan — next month

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What should I focus on next month?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Next Period Plan (Last 30 Days)",
      "response": "Monthly action plan:\n1. Sleep — the biggest gap; build a wind-down routine and target 8h consistently\n2. Water — small habit: a glass before each meal closes most of the deficit\n3. Resting HR — sustained cardio 3x/week will bring this down over a month\n4. Steps — you're close to 10,000; a 15-minute evening walk seals it"
    }
  ]
}
```

---

#### Single metric lookup — sleep over last 2 weeks

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How long did I sleep on average over the last 2 weeks?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Metric Lookup (Last 14 Days)",
      "response": "Your average sleep over the last 14 days was 7.0 hours per night."
    }
  ]
}
```

---

#### Metric comparison — steps vs optimal

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How do my steps compare to the optimal target?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Metric Comparison (Last 30 Days)",
      "response": "Your average daily steps over the last 30 days: 9,300. Optimal target: 10,000. You're 700 steps (7%) below target — adding a short 10-minute walk to your day would close that gap entirely."
    }
  ]
}
```

---

#### Multi-metric deep dive — last month

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "Break down all my metrics in detail."}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Deep Dive (Last 30 Days)",
      "response": "**Sleep:** 7.1h avg vs 8h target — gap: -0.9h. Consistently below target; the most impactful area to address.\n\n**Steps:** 9,300 avg vs 10,000 target — gap: -700. Close to target; small daily habit change would close it.\n\n**Resting HR:** 68 bpm avg vs 60 bpm target — gap: +8 bpm. Elevated; improved sleep and aerobic fitness will bring this down.\n\n**Water:** 2.1L avg vs 2.5L target — gap: -0.4L. Consistent small deficit; easy to fix with a structured drinking habit.\n\n**Workouts:** good frequency — on track.\n\n**HRV:** not logged on multiple days — no reliable average available. Start logging daily for trend data.\n\n**Overall:** a solid month. Sleep and HRV logging are the top priorities."
    }
  ]
}
```

---

#### Compound — performance summary last week + next period plan

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last week and what should I focus on next month?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary (Last 7 Days)",
      "response": "Last week at a glance:\n- Sleep: 6.8h avg — below the 8h target\n- Steps: 9,400 avg — close to 10,000\n- Resting HR: 69 bpm — above the 60 bpm target\n- Water: 2.1L — below the 2.5L target\n- Workouts: 4 of 7 days\n- HRV: incomplete logging this week\n\nA decent week overall — hydration and sleep are the main gaps."
    },
    {
      "label": "Next Period Plan (Last 30 Days)",
      "response": "For next month, focus on:\n1. Sleep — set a fixed bedtime; even 30 extra minutes makes a measurable difference\n2. Hydration — 2.5L daily; a morning glass and one with each meal gets you there\n3. Resting HR — sustained cardio will lower this over 4 weeks\n4. HRV logging — start tracking daily so you have a full month of data"
    }
  ]
}
```

---

#### Rejection — off-topic

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What is the weather like today?"}'
```

```json
{
  "valid": false,
  "reason": "That question is not related to your health metrics. I can only answer questions about your personal health data."
}
```

HTTP status: `200`

---

#### Rejection — out-of-range (older than 30 days)

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What were my metrics 6 months ago?"}'
```

```json
{
  "valid": false,
  "reason": "This app only supports data from the last 30 days. Data from 6 months ago is not available."
}
```

---

#### Rejection — cross-user query

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did user 2 do last week?"}'
```

```json
{
  "valid": false,
  "reason": "You can only access your own health data."
}
```

---

#### Unknown user

**Fly.io:**
```bash
curl -X POST https://weekly-health-tracker.fly.dev/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "999", "prompt": "How did I do?"}'
```

```json
{
  "error": "User not found"
}
```

HTTP status: `404`

---

## Demo users

| user_id | Profile |
|---------|---------|
| `1` | Moderate performer — HRV unlogged on ~half the days |
| `2` | High performer — all metrics logged every day |
| `3` | Struggling performer — sleep and HRV frequently unlogged |

Switch users via the `user_id` field in the request body, or via URL param for the metrics endpoint:

```bash
curl https://weekly-health-tracker.fly.dev/metrics/2
```

---

## Deployment on Fly.io

### 1. Install the Fly CLI

```bash
brew install flyctl        # macOS
# or: curl -L https://fly.io/install.sh | sh
```

### 2. Log in

```bash
fly auth login
```

### 3. Launch the app (first time only)

From the project root:

```bash
fly launch
```

Fly will detect the `Dockerfile` and `fly.toml`. Accept the defaults or adjust the region. **Do not deploy yet** when prompted — set the secret first.

### 4. Set the API key as a Fly secret

```bash
fly secrets set DEEPSEEK_API_KEY=sk-your-key-here
```

Verify it was set:

```bash
fly secrets list
```

### 5. Deploy

```bash
fly deploy
```

### 6. Check it's running

```bash
fly status
fly logs
```

### Subsequent deploys

```bash
fly deploy
```

### Rotating the API key

```bash
fly secrets set DEEPSEEK_API_KEY=sk-new-key-here
```

Fly automatically restarts the app with the new value.

---

## Project structure

```
/
├── api.py                  # FastAPI app — GET /metrics/{user_id}, POST /chat
├── classifier.py           # Prompt validation + decomposition via raw DeepSeek call
├── data_store.py           # Hardcoded in-memory 30-day metrics and optimal targets
├── prompt_registry.py      # LangChain ChatPromptTemplates per intent
├── chain_executor.py       # LCEL chains + RunnableParallel execution
├── response_assembler.py   # Pure string formatting of labelled blocks
├── Dockerfile              # Container image for deployment
├── fly.toml                # Fly.io app configuration
├── requirements.txt        # Python dependencies
├── Makefile                # Dev, test, and smoke-test commands
├── docs/
│   ├── prd.md
│   └── prd-issues.md
└── tests/
    ├── test_data_store.py
    ├── test_api_metrics.py
    ├── test_classifier.py
    ├── test_prompt_registry.py
    ├── test_chain_executor.py
    ├── test_response_assembler.py
    └── test_api_chat.py
```
