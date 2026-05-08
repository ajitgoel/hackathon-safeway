"""
chain_executor.py — Build and run LangChain LCEL chains concurrently.

For each sub-request from the classifier:
  1. Look up the intent in prompt_registry to get the ChatPromptTemplate.
  2. Build an LCEL chain:  prompt | llm
  3. Run all chains concurrently via RunnableParallel.
  4. Return an ordered list of {intent, label, response} matching input order.

DeepSeek is accessed via ChatOpenAI (OpenAI-compatible) with:
  base_url  = "https://api.deepseek.com"
  api_key   = DEEPSEEK_API_KEY environment variable
  model     = "deepseek-chat"
"""

import os
from typing import Optional

from langchain_community.chat_models import ChatOpenAI
from langchain_core.runnables import RunnableParallel

from data_store import get_optimal_targets, get_user_metrics
from prompt_registry import INTENT_LABELS, PROMPT_REGISTRY

# ---------------------------------------------------------------------------
# Type alias for a sub-request (matches classifier output shape)
# SubRequest = {"intent": str, "focus_metric": str | None}
# Result     = {"intent": str, "label": str, "response": str}
# ---------------------------------------------------------------------------


def _build_llm() -> ChatOpenAI:
    """Instantiate the DeepSeek-backed ChatOpenAI model.

    Raises:
        EnvironmentError: If DEEPSEEK_API_KEY is not set.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY environment variable is not set.")

    return ChatOpenAI(
        model_name="deepseek-chat",
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com",
        temperature=0.7,
    )


def execute_chains(
    user_id: str,
    sub_requests: list[dict],
) -> list[dict]:
    """Run one LCEL chain per sub-request concurrently via RunnableParallel.

    Args:
        user_id:      The user whose metrics are injected into every chain.
        sub_requests: Ordered list of {"intent": str, "focus_metric": str | None}
                      as returned by the classifier.

    Returns:
        Ordered list of {"intent": str, "label": str, "response": str}
        in the same order as sub_requests.

    Raises:
        EnvironmentError: If DEEPSEEK_API_KEY is not set.
        ValueError:       If an intent is not found in PROMPT_REGISTRY.
        KeyError:         If user_id is not found in the data store.
    """
    if not sub_requests:
        return []

    # Validate all intents up-front before touching the LLM
    for sub_req in sub_requests:
        intent = sub_req["intent"]
        if intent not in PROMPT_REGISTRY:
            raise ValueError(
                f"Unknown intent '{intent}'. "
                f"Valid intents: {sorted(PROMPT_REGISTRY.keys())}"
            )

    # Fetch data once — injected into every chain input
    # (raises KeyError for unknown user_id before we touch the LLM)
    user_metrics = get_user_metrics(user_id)
    optimal_targets = get_optimal_targets()

    llm = _build_llm()

    # Build one LCEL chain per sub-request and record the ordered keys
    ordered_keys: list[str] = []
    chains: dict[str, object] = {}

    for idx, sub_req in enumerate(sub_requests):
        intent: str = sub_req["intent"]
        focus_metric: Optional[str] = sub_req.get("focus_metric") or ""

        # Use a stable key that preserves order even when the same intent
        # appears more than once in a compound request.
        key = f"{idx}__{intent}"
        ordered_keys.append(key)

        prompt = PROMPT_REGISTRY[intent]
        # LCEL chain: format the prompt then call the LLM
        chain = prompt | llm

        # Bind the input variables so RunnableParallel receives a single
        # shared input dict and each chain extracts what it needs.
        chains[key] = chain.bind(
            user_metrics=str(user_metrics),
            optimal_targets=str(optimal_targets),
            focus_metric=focus_metric,
        )

    # Run all chains concurrently
    parallel = RunnableParallel(**chains)
    # RunnableParallel with bound chains needs an empty input dict
    raw_results: dict = parallel.invoke({})

    # Reassemble in input order, extracting the text content from each AIMessage
    results: list[dict] = []
    for idx, key in enumerate(ordered_keys):
        intent = sub_requests[idx]["intent"]
        ai_message = raw_results[key]
        # AIMessage has a .content attribute; handle both str and AIMessage
        response_text = (
            ai_message.content
            if hasattr(ai_message, "content")
            else str(ai_message)
        )
        results.append(
            {
                "intent": intent,
                "label": INTENT_LABELS[intent],
                "response": response_text,
            }
        )

    return results
