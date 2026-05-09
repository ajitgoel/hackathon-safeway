"""
chain_executor.py — Build and run LangChain LCEL chains concurrently.

For each sub-request from the classifier:
  1. Fetch the full 30-day list from data_store and slice the most recent
     duration_days entries.
  2. Build a duration_label string (e.g. "the last 7 days").
  3. Look up the intent in prompt_registry to get the ChatPromptTemplate.
  4. Build an LCEL chain:  prompt | llm
  5. Run all chains concurrently via RunnableParallel.
  6. Return an ordered list of {intent, label, response} matching input order.

Groq is accessed via ChatOpenAI (OpenAI-compatible) with:
  base_url  = "https://api.groq.com/openai/v1"
  api_key   = GROQ_API_KEY environment variable
  model     = "llama-3.3-70b-versatile"

Performance notes:
  - The ChatOpenAI instance is created once at module level and reused across
    all requests (connection pool reuse, no per-request setup overhead).
  - execute_chains is async so it runs on the FastAPI event loop without
    blocking the threadpool.
  - RunnableParallel fans out all sub-request chains concurrently.
"""

import asyncio
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableParallel

from data_store import get_optimal_targets, get_user_metrics
from prompt_registry import INTENT_LABEL_TEMPLATES, PROMPT_REGISTRY


# ---------------------------------------------------------------------------
# Module-level LLM singleton — instantiated once, reused across all requests.
# ---------------------------------------------------------------------------

_llm: Optional[ChatOpenAI] = None


def _get_llm() -> ChatOpenAI:
    """Return the module-level ChatOpenAI singleton, creating it on first call.

    Raises:
        EnvironmentError: If GROQ_API_KEY is not set.
    """
    global _llm
    if _llm is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable is not set.")
        _llm = ChatOpenAI(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=0.7,
        )
    return _llm


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def _duration_label(duration_days: int) -> str:
    """Convert a duration_days integer to a human-readable label.

    Examples:
        7  → "the last 7 days"
        14 → "the last 14 days"
        30 → "the last 30 days"
    """
    return f"the last {duration_days} days"


def _build_label(intent: str, duration_days: int) -> str:
    """Combine the intent's base label with a capitalised duration suffix.

    Examples:
        ("performance_summary", 7)  → "Performance Summary (Last 7 Days)"
        ("next_period_plan",    30) → "Next Period Plan (Last 30 Days)"
    """
    base = INTENT_LABEL_TEMPLATES[intent]
    return f"{base} (Last {duration_days} Days)"


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

async def execute_chains(
    user_id: str,
    sub_requests: list[dict],
) -> list[dict]:
    """Run one LCEL chain per sub-request concurrently via RunnableParallel.

    Async so the FastAPI event loop is not blocked while waiting for DeepSeek
    responses. RunnableParallel fans out all chains in parallel, so a compound
    request with N sub-requests takes roughly the same time as a single one.

    Args:
        user_id:      The user whose metrics are injected into every chain.
        sub_requests: Ordered list of dicts, each with:
                        intent        (str)
                        focus_metric  (str | None)
                        duration_days (int)
                      as returned by the classifier.

    Returns:
        Ordered list of {"intent": str, "label": str, "response": str}
        in the same order as sub_requests.

    Raises:
        EnvironmentError: If GROQ_API_KEY is not set.
        ValueError:       If an intent is not found in PROMPT_REGISTRY.
        KeyError:         If user_id is not found in the data store.
    """
    if not sub_requests:
        return []

    # Validate all intents up-front before touching the LLM or data store.
    for sub_req in sub_requests:
        intent = sub_req["intent"]
        if intent not in PROMPT_REGISTRY:
            raise ValueError(
                f"Unknown intent '{intent}'. "
                f"Valid intents: {sorted(PROMPT_REGISTRY.keys())}"
            )

    # Fetch data and get the LLM singleton — both are fast/local operations.
    all_metrics = get_user_metrics(user_id)
    optimal_targets = get_optimal_targets()
    llm = _get_llm()

    # Build one LCEL chain per sub-request.
    # Use a positional prefix in the key so the same intent can appear twice
    # in a compound request without collision.
    ordered_keys: list[str] = []
    chains: dict[str, object] = {}

    for idx, sub_req in enumerate(sub_requests):
        intent: str = sub_req["intent"]
        focus_metric: Optional[str] = sub_req.get("focus_metric") or ""
        duration_days: int = sub_req.get("duration_days", 30)

        # Slice the most recent duration_days entries (data is oldest-first).
        sliced_metrics = all_metrics[-duration_days:]
        dur_label = _duration_label(duration_days)

        key = f"{idx}__{intent}"
        ordered_keys.append(key)

        prompt = PROMPT_REGISTRY[intent]
        chain = prompt | llm

        # Capture all inputs in a closure so each chain uses its own
        # pre-filled variables regardless of RunnableParallel's shared input.
        captured_input = {
            "user_metrics": str(sliced_metrics),
            "optimal_targets": str(optimal_targets),
            "focus_metric": focus_metric,
            "duration_label": dur_label,
        }
        chains[key] = RunnableLambda(
            lambda _inp, c=chain, ci=captured_input: c.invoke(ci)
        )

    # Run all chains concurrently in a threadpool so the async event loop
    # is not blocked by LangChain's synchronous invoke calls.
    parallel = RunnableParallel(**chains)
    raw_results: dict = await asyncio.to_thread(parallel.invoke, {})

    # Reassemble in input order, extracting text from each AIMessage.
    results: list[dict] = []
    for idx, key in enumerate(ordered_keys):
        sub_req = sub_requests[idx]
        intent = sub_req["intent"]
        duration_days = sub_req.get("duration_days", 30)

        ai_message = raw_results[key]
        response_text = (
            ai_message.content
            if hasattr(ai_message, "content")
            else str(ai_message)
        )
        results.append(
            {
                "intent": intent,
                "label": _build_label(intent, duration_days),
                "response": response_text,
            }
        )

    return results
