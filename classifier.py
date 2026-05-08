"""
classifier.py — Validate and decompose a user prompt into typed sub-requests.

Makes a single raw HTTP call to the DeepSeek API (not wrapped in LangChain)
so the classifier stays independent and easily unit-testable via mocked responses.

Public interface:
    classify(user_id: str, prompt: str) -> ClassifierResult
"""

import json
import os

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_INTENTS = frozenset(
    {
        "performance_summary",
        "next_period_plan",
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
You are a classifier for a personal health tracker app.

DATA AVAILABLE: The app stores exactly 30 days of daily health data for the current user.
Any request for data within the last 30 days is valid. "Last week" (7 days), "last 2 weeks"
(14 days), and "last month" (30 days) are ALL valid requests — do NOT reject them.
Only reject requests that ask for data older than 30 days (e.g. "6 months ago", "last year").

Metrics available: sleep (hours), steps, resting_hr (bpm), water (litres), workouts (count), hrv (ms).

Your job is to classify the user's message and return ONLY a JSON object — no preamble, no explanation, no markdown fences.

Valid intents:
- performance_summary     : overall review of metrics vs targets for a period
- next_period_plan        : prioritised action plan for the coming period
- single_metric_lookup    : retrieve the value of one specific metric
- metric_comparison       : compare one specific metric against its optimal target
- multi_metric_deep_dive  : comprehensive breakdown of all metrics in detail

Duration extraction rules (apply per sub-request):
- "last week"              → duration_days: 7   (VALID — within 30-day window)
- "last 2 weeks"           → duration_days: 14  (VALID — within 30-day window)
- "last month"             → duration_days: 30  (VALID — within 30-day window)
- No duration mentioned    → duration_days: 30  (default, always valid)
- More than 30 days        → valid: false (out of range — the only out-of-range case)

Rejection rules (set valid=false):
- Off-topic questions unrelated to the user's own health metrics
- Requests for data strictly older than 30 days (e.g. "6 months ago", "last year", "2 months ago")
- Requests about another user's data

IMPORTANT: "last week", "last 2 weeks", and "last month" are all within the 30-day window.
Never reject these as out of range.

Output schema (strict JSON, no extra keys):
{
  "valid": true | false,
  "reason": null | "<human-readable rejection reason>",
  "sub_requests": [
    {
      "intent": "<intent>",
      "focus_metric": "<metric_name> | null",
      "duration_days": <integer>
    }
  ]
}

Rules:
- If valid=false, sub_requests must be an empty array and reason must be a non-empty string.
- If valid=true, reason must be null and sub_requests must contain at least one item.
- A compound message (e.g. "How did I do last week AND what's my plan for next month?") produces
  multiple sub_requests, each with their own duration_days extracted from that part of the message.
- focus_metric is only non-null for single_metric_lookup and metric_comparison intents.
- duration_days must always be an integer (never null or a string).
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
            sub_requests (list of {intent: str, focus_metric: str | None, duration_days: int})

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
