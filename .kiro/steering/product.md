# Product: Minimal LLM-Powered Weekly Health Tracker

A hackathon MVP that lets users query their weekly health metrics via a conversational chat interface. Users can ask natural-language questions about their data and receive structured, LLM-generated responses.

## Core Capabilities

- View raw weekly health metrics on a summary screen
- Ask natural-language questions about personal health data (current week only)
- Classifier validates and decomposes prompts into typed sub-requests
- LangChain routes each intent to the appropriate prompt template
- DeepSeek generates responses; compound questions return multiple labelled blocks

## Metrics Tracked

`sleep` (hours), `steps`, `resting_hr` (bpm), `water` (litres), `workouts` (count), `hrv` (ms)

## Supported Intents

`performance_summary`, `next_week_plan`, `single_metric_lookup`, `metric_comparison`, `multi_metric_deep_dive`

## Scope Boundaries

- Current week data only — no historical queries
- Single user per session — no cross-user queries
- No authentication, no database, no persistent storage
- No frontend (React is out of scope)
- Only the 6 defined metrics are supported
