```mermaid
flowchart TB
    subgraph API_LAYER["API layer · FastAPI"]
        API["api
        ─────────────────────────
        GET /metrics/{user_id}
        POST /chat"]
    end

    subgraph CORE["Core modules · Python / LangChain"]
        direction LR
        CL["classifier
        ─────────────────────────
        • Validates prompt scope
        • Decomposes into sub-requests
        • Extracts duration_days per intent
          (e.g. 'last week' → 7)
        • Returns structured JSON"]

        PR["prompt_registry
        ─────────────────────────
        • 5 ChatPromptTemplates
          (one per intent)
        • Injects: user_metrics,
          optimal_targets,
          focus_metric, duration_label
        • Instructs LLM to acknowledge
          null metrics explicitly"]

        CE["chain_executor
        ─────────────────────────
        • Slices most recent N days
          of data per sub-request
        • Builds duration_label string
        • Looks up template in registry
        • Runs all chains concurrently
          via RunnableParallel
        • Returns ordered results"]

        RA["response_assembler
        ─────────────────────────
        • Pure string formatting
        • Renders labelled blocks:
          **Label:**
          response text
        • No LLM involvement"]

        DS[("data_store
        ─────────────────────────
        • 30 daily metric entries
          per user (in-memory)
        • Metrics: sleep, steps,
          resting_hr, water,
          workouts, hrv
        • None = unlogged day
        • get_user_metrics()
        • get_optimal_targets()")]
    end

    EXT(["DeepSeek API
    deepseek-chat"])

    API -->|"① GET: get_user_metrics(user_id)"| DS
    API -->|"② POST: user_id + prompt"| CL
    CL -->|"③ raw HTTP · classify + extract duration_days"| EXT
    API -->|"④ sub_requests (intent, focus_metric, duration_days)"| CE
    CE -->|"⑤ get_user_metrics() · full 30-day list"| DS
    CE -->|"⑥ lookup intent → ChatPromptTemplate"| PR
    CE -->|"⑦ ChatOpenAI · one call per sub-request (parallel)"| EXT
    API -->|"⑧ ordered results list"| RA

    style EXT fill:#FAECE7,stroke:#D85A30,color:#4A1B0C
    style API fill:#EAF3DE,stroke:#639922,color:#173404
```

## Request flow — step by step

| Step | From → To | What happens |
|------|-----------|--------------|
| ① | `api` → `data_store` | `GET /metrics` fetches the full 30-day list for the user |
| ② | `api` → `classifier` | `POST /chat` forwards `user_id` + raw prompt |
| ③ | `classifier` → DeepSeek | Raw HTTP call; DeepSeek validates scope, decomposes into sub-requests, and extracts `duration_days` per intent (e.g. "last week" → `7`, "last 2 weeks" → `14`, no duration → `30`). Returns structured JSON only. |
| ④ | `api` → `chain_executor` | Passes the list of sub-requests, each carrying `intent`, `focus_metric`, and `duration_days` |
| ⑤ | `chain_executor` → `data_store` | Fetches full 30-day list, then **slices the most recent `duration_days` entries** per sub-request |
| ⑥ | `chain_executor` → `prompt_registry` | Looks up the `ChatPromptTemplate` for each intent; injects sliced metrics, optimal targets, focus metric, and a human-readable `duration_label` |
| ⑦ | `chain_executor` → DeepSeek | All chains run **concurrently via `RunnableParallel`**; results are reordered to match input order |
| ⑧ | `api` → `response_assembler` | Passes ordered `{intent, label, response}` list; assembler formats into labelled blocks (`**Label:**\nresponse`) with no further LLM calls |
