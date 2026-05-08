# Project Structure

```
/
├── api.py                  # FastAPI app — GET /metrics/{user_id}, POST /chat
├── classifier.py           # Prompt validation + decomposition via raw DeepSeek call
├── data_store.py           # Hardcoded in-memory user metrics and optimal targets
├── prompt_registry.py      # (planned) Dict of LangChain ChatPromptTemplates per intent
├── chain_executor.py       # (planned) Builds LLMChains, runs via RunnableParallel
├── response_assembler.py   # (planned) Formats ordered results into labelled blocks
├── docs/
│   ├── prd.md              # Full product requirements document
│   └── prd-issues.md       # GitHub-style issues tracking implementation tasks
└── tests/
    ├── test_data_store.py  # Unit tests for data_store
    └── test_api_metrics.py # Integration tests for GET /metrics endpoint
```

## Module Responsibilities

| Module | Role |
|---|---|
| `data_store` | Single source of truth for user metrics and optimal targets |
| `classifier` | Validates prompts and returns structured `{valid, reason, sub_requests}` |
| `prompt_registry` | Maps intent strings to LangChain `ChatPromptTemplate` instances |
| `chain_executor` | Builds and runs chains concurrently; returns ordered `{intent, label, response}` list |
| `response_assembler` | Pure string formatting — no LLM; produces labelled block output |
| `api` | FastAPI entry point; wires all modules together |

## Conventions

- All modules live at the project root (flat structure — no `src/` wrapper)
- Tests live in `tests/` and mirror the module they test (`test_<module>.py`)
- External dependencies (DeepSeek API) are mocked in unit tests via `unittest.mock` or `pytest` fixtures
- `None` represents an unlogged metric — never omit the key, always return/serialise as `null`
- Returned dicts from `data_store` are always shallow copies to prevent mutation of internal state
- `user_id` is always a string, even when it looks numeric (`"1"`, not `1`)
