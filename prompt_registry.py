"""
prompt_registry.py — LangChain ChatPromptTemplates for each supported intent.

Each template receives three input variables:
  user_metrics    : dict of the user's weekly metrics (values may be None)
  optimal_targets : dict of expert-defined optimal target values
  focus_metric    : name of the specific metric in focus (may be None / empty
                    string for intents that don't target a single metric)

Every template's system message explicitly instructs the LLM to acknowledge
any metric whose value is None rather than silently skipping it.
"""

from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Shared null-metric instruction — baked into every template
# ---------------------------------------------------------------------------

_NULL_METRIC_INSTRUCTION = (
    "IMPORTANT: Some metrics may have a value of None, meaning the user did not "
    "log that metric this week. For any such metric, explicitly acknowledge it "
    "(e.g. 'You didn't log HRV this week') and do not attempt to analyse or "
    "compare it. Never silently skip a missing metric."
)

# ---------------------------------------------------------------------------
# Intent → human-readable label (used by chain_executor to label blocks)
# ---------------------------------------------------------------------------

INTENT_LABELS: dict[str, str] = {
    "performance_summary": "Performance Summary",
    "next_week_plan": "Next Week Plan",
    "single_metric_lookup": "Metric Lookup",
    "metric_comparison": "Metric Comparison",
    "multi_metric_deep_dive": "Deep Dive",
}

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_PERFORMANCE_SUMMARY = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health coach reviewing a user's weekly metrics. "
                "Compare each metric against its optimal target and give an honest, "
                "encouraging summary of how the user performed overall. "
                "Be concise — use bullet points for each metric, then a short "
                "overall verdict. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my health metrics for last week:\n{user_metrics}\n\n"
                "Optimal targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "How did I do last week?"
            ),
        ),
    ]
)

_NEXT_WEEK_PLAN = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health coach creating a prioritised action plan. "
                "Identify the metrics furthest from their optimal targets and suggest "
                "specific, realistic improvements for next week. "
                "Order recommendations by impact — biggest gap first. "
                "Be practical and motivating. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my health metrics for last week:\n{user_metrics}\n\n"
                "Optimal targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "What should I focus on next week?"
            ),
        ),
    ]
)

_SINGLE_METRIC_LOOKUP = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health assistant. "
                "The user wants to know the value of a specific metric from last week. "
                "Give a direct, factual answer for the requested metric only. "
                "Include the unit (e.g. hours, steps, bpm, litres, ms). "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my health metrics for last week:\n{user_metrics}\n\n"
                "Optimal targets:\n{optimal_targets}\n\n"
                "What was my {focus_metric} last week?"
            ),
        ),
    ]
)

_METRIC_COMPARISON = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health assistant. "
                "The user wants to compare a specific metric against its optimal target. "
                "State the user's actual value, the optimal target, and the delta "
                "(how far above or below target they are). "
                "Give a one-sentence interpretation of what that gap means. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my health metrics for last week:\n{user_metrics}\n\n"
                "Optimal targets:\n{optimal_targets}\n\n"
                "How does my {focus_metric} compare to the optimal target?"
            ),
        ),
    ]
)

_MULTI_METRIC_DEEP_DIVE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health coach conducting a comprehensive weekly review. "
                "For every metric, provide: the user's actual value, the optimal target, "
                "the gap, and a brief interpretation. "
                "Then close with a short overall assessment and top insight. "
                "Use a structured format with one section per metric. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my health metrics for last week:\n{user_metrics}\n\n"
                "Optimal targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "Give me a detailed breakdown of all my metrics."
            ),
        ),
    ]
)

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

PROMPT_REGISTRY: dict[str, ChatPromptTemplate] = {
    "performance_summary": _PERFORMANCE_SUMMARY,
    "next_week_plan": _NEXT_WEEK_PLAN,
    "single_metric_lookup": _SINGLE_METRIC_LOOKUP,
    "metric_comparison": _METRIC_COMPARISON,
    "multi_metric_deep_dive": _MULTI_METRIC_DEEP_DIVE,
}
