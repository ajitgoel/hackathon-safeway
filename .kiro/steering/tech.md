# Tech Stack

## Language & Runtime
- Python 3.10+

## Frameworks & Libraries
- **FastAPI** — HTTP API framework
- **LangChain** (`langchain` + `langchain-openai`) — prompt templates, chain construction, parallel execution
- **Groq** — LLM provider (`llama-3.3-70b-versatile` model)
  - Classifier: raw HTTP via `httpx` (not LangChain)
  - Chain executor: via `ChatOpenAI` with `base_url="https://api.groq.com/openai/v1"` (OpenAI-compatible)
- **pytest** — test runner
- **httpx** / FastAPI `TestClient` — API integration testing

## Environment Variables
- `GROQ_API_KEY` — required at runtime; never hardcoded

## Common Commands

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_data_store.py

# Run the API server (development)
uvicorn api:app --reload
```

## Key Architectural Constraints
- Classifier makes a **raw `httpx` call** to Groq — not wrapped in LangChain — to keep it independently testable
- LangChain is used **only** for prompt templates, chain construction, and `RunnableParallel` execution
- Every `POST /chat` is **stateless** — full metrics + targets context is injected per call
- No database; all data is hardcoded in-memory in `data_store.py`
