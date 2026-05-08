# Weekly Health Tracker

A minimal LLM-powered API that lets users query their weekly health metrics via natural language. Built with FastAPI, LangChain, and DeepSeek.

## Prerequisites

- Python 3.10+
- A [DeepSeek API key](https://platform.deepseek.com/)

## Local setup

```bash
pip install fastapi uvicorn langchain langchain-community pydantic requests httpx
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

### `GET /metrics/{user_id}`

Returns the raw weekly health metrics for a user.

**Example — known user:**

```bash
curl http://localhost:8000/metrics/1
```

```json
{
  "sleep": 6.5,
  "steps": 8200,
  "resting_hr": 72,
  "water": 1.8,
  "workouts": 3,
  "hrv": null
}
```

**Example — unknown user:**

```bash
curl http://localhost:8000/metrics/999
```

```json
{
  "error": "User not found"
}
```

HTTP status: `404`

---

### `POST /chat`

Classifies a natural-language prompt, routes it to the appropriate LangChain prompt template(s), calls DeepSeek, and returns labelled response blocks.

**Request body:**

```json
{
  "user_id": "1",
  "prompt": "How did I do last week?"
}
```

---

**Valid single-intent prompt:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last week?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary",
      "response": "Here's how you did last week:\n- Sleep: 6.5h (target 8h) — below target by 1.5h\n- Steps: 8,200 (target 10,000) — 1,800 short\n- Resting HR: 72 bpm (target 60 bpm) — above target\n- Water: 1.8L (target 2.5L) — below target\n- Workouts: 3 (target 5) — below target\n- HRV: not logged this week\n\nOverall: a moderate week with room to improve on sleep, hydration, and activity."
    }
  ]
}
```

---

**Valid compound prompt (multiple intents):**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How did I do last week and what should I focus on next week?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Performance Summary",
      "response": "Here's how you did last week: ..."
    },
    {
      "label": "Next Week Plan",
      "response": "Top priorities for next week:\n1. Sleep — aim for 8h by setting a consistent bedtime\n2. Workouts — add 2 more sessions\n3. Water — carry a 500ml bottle and refill 5x daily"
    }
  ]
}
```

---

**Single metric lookup:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How long did I sleep on average last week?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Metric Lookup",
      "response": "You slept an average of 6.5 hours last week."
    }
  ]
}
```

---

**Metric comparison:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "How do my steps compare to the optimal target?"}'
```

```json
{
  "valid": true,
  "blocks": [
    {
      "label": "Metric Comparison",
      "response": "Your steps last week: 8,200. Optimal target: 10,000. You were 1,800 steps (18%) below target — a solid base, but adding a short 20-minute walk daily would close that gap."
    }
  ]
}
```

---

**Off-topic prompt (rejected):**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What is the weather like today?"}'
```

```json
{
  "valid": false,
  "reason": "That question is not related to your health metrics. I can only answer questions about your weekly health data."
}
```

HTTP status: `200`

---

**Out-of-range prompt (rejected):**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "prompt": "What were my metrics 6 months ago?"}'
```

```json
{
  "valid": false,
  "reason": "This app only has data for the current week. Historical data is not available."
}
```

---

**Unknown user:**

```bash
curl -X POST http://localhost:8000/chat \
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

| user_id | Notes |
|---------|-------|
| `1` | Moderate performer, HRV not logged |
| `2` | All metrics logged, high performer |
| `3` | Sleep not logged, low activity |

Switch users via the `user_id` field in the request body, or via URL param for the metrics endpoint: `GET /metrics/2`.

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

Secrets are injected as environment variables at runtime and never stored in your image or repo:

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
├── api.py                  # FastAPI app — GET /metrics, POST /chat
├── classifier.py           # Prompt validation via raw DeepSeek call
├── data_store.py           # Hardcoded in-memory user metrics and targets
├── prompt_registry.py      # LangChain ChatPromptTemplates per intent
├── chain_executor.py       # LCEL chains + RunnableParallel execution
├── response_assembler.py   # Pure string formatting of labelled blocks
├── Dockerfile              # Container image for deployment
├── fly.toml                # Fly.io app configuration
├── docs/
│   ├── prd.md
│   └── prd-issues.md
└── tests/
```
