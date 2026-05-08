"""
classifier.py — Validate and decompose a user prompt into typed sub-requests.

Makes a single raw HTTP call to the DeepSeek API (not wrapped in LangChain)
so the classifier stays independent and easily unit-testable via mocked responses.

Public interface:
    classify(user_id: str, prompt: str) -> ClassifierResult
"""

import json
import os
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Types (plain dicts — no Pydantic dependency required here)
# ---------------------------------------------------------------------------

# SubRequest = {"intent": str, "focus_metric": str | None}
# ClassifierResult = {"valid": bool, "reason": str | None, "sub_requests": list[SubRequest]}

VALID_INTENTS = frozenset(
    {
        "performance_summary",
        "next_week_plan",
        "single_metric_lookup",
        "metric_comparison",
        "multi_metric_deep_dive",
    }
)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a classifier for a personal weekly health tracker app.

The app only knows about a single user's health data for the CURRENT week.
Metrics available: sleep (hours), steps, resting_hr (bpm), water (litres), workouts (count), hrv (ms).

Your job is to classify the user's message and return ONLY a JSON object — no preamble, no explanation, no markdown fences.

Valid intents:
- performance_summary     : overall review of last week's metrics vs targets
- next_week_plan          : prioritised action plan for the coming week
- single_metric_lookup    : retrieve the value of one specific metric
- metric_comparison       : compare one specific metric against its optimal target
- multi_metric_deep_dive  : comprehensive breakdown of all metrics in detail

Rejection rules (set valid=false):
- Off-topic questions unrelated to the user's own health metrics
- Requests for historical data beyond the current week
- Requests about another user's data

Output schema (strict JSON, no extra keys):
{
  "valid": true | false,
  "reason": null | "<human-readable rejection reason>",
  "sub_requests": [
    {"intent": "<intent>", "focus_metric": "<metric_name> | null"}
  ]
}

Rules:
- If valid=false, sub_requests must be an empty array and reason must be a non-empty string.
- If valid=true, reason must be null and sub_requests must contain at least one item.
- A compound message (e.g. "How did I do AND what's my plan?") produces multiple sub_requests.
- focus_metric is only non-null for single_metric_lookup and metric_comparison intents.
- Return ONLY the JSON object. No markdown, no code fences, no extra text.
"""


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def classify(user_id: str, prompt: str) -> dict:
    """Classify a user prompt into typed sub-requests via a raw DeepSeek API call.

    Args:
        user_id: The ID of the requesting user (included for context).
        prompt:  The natural-language question from the user.

    Returns:
        A dict with keys:
            valid        (bool)
            reason       (str | None)
            sub_requests (list of {intent: str, focus_metric: str | None})

    Raises:
        EnvironmentError: If DEEPSEEK_API_KEY is not set.
        RuntimeError:     If the API call fails or returns unparseable JSON.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY environment variable is not set."
        )

    user_message = (
        f"User ID: {user_id}\n"
        f"User message: {prompt}"
    )

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0,  # deterministic output for classification
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"DeepSeek API request failed: {exc}") from exc

    raw_content = response.json()["choices"][0]["message"]["content"].strip()

    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Classifier returned non-JSON response: {raw_content!r}"
        ) from exc

    return result
