"""
prompt_registry.py — LangChain ChatPromptTemplates for each supported intent.

Each template receives four input variables:
  user_metrics    : pre-sliced list of daily metric dicts for the period
  optimal_targets : dict of expert-defined optimal daily target values
  focus_metric    : name of the specific metric in focus (None / empty string
                    for intents that don't target a single metric)
  duration_label  : human-readable period string, e.g. "the last 7 days"

Every template's system message explicitly instructs the LLM to acknowledge
any metric whose value is None rather than silently skipping it.
"""

from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Shared null-metric instruction — baked into every template
# ---------------------------------------------------------------------------

_NULL_METRIC_INSTRUCTION = (
    "IMPORTANT: Some metrics may have a value of None for certain days, meaning "
    "the user did not log that metric on those days. For any such metric, "
    "explicitly acknowledge it (e.g. 'You didn't log HRV for some days in this "
    "period') and do not attempt to analyse or compare it. Never silently skip "
    "a missing metric."
)

# ---------------------------------------------------------------------------
# Intent → human-readable label template
# (chain_executor fills in the duration when building the final label)
# ---------------------------------------------------------------------------

INTENT_LABEL_TEMPLATES: dict[str, str] = {
    "performance_summary":    "Performance Summary",
    "next_period_plan":       "Next Period Plan",
    "single_metric_lookup":   "Metric Lookup",
    "metric_comparison":      "Metric Comparison",
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
                "You are a personal health coach reviewing a user's health metrics. "
                "Compare each metric against its optimal daily target and give an "
                "honest, encouraging summary of how the user performed overall for "
                "the period. "
                "Be concise — use bullet points for each metric, then a short "
                "overall verdict. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my daily health metrics for {duration_label}:\n{user_metrics}\n\n"
                "Optimal daily targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "How did I do over {duration_label}?"
            ),
        ),
    ]
)

_NEXT_PERIOD_PLAN = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health coach creating a prioritised action plan. "
                "Based on the user's metrics for the period, identify the areas "
                "furthest from their optimal targets and suggest specific, realistic "
                "improvements for the coming period. "
                "Order recommendations by impact — biggest gap first. "
                "Be practical and motivating. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my daily health metrics for {duration_label}:\n{user_metrics}\n\n"
                "Optimal daily targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "Based on my data for {duration_label}, what should I focus on going forward?"
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
                "The user wants to know the average (or total, where appropriate) "
                "value of a specific metric over the period. "
                "Give a direct, factual answer for the requested metric only. "
                "Include the unit (e.g. hours, steps, bpm, litres, ms). "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my daily health metrics for {duration_label}:\n{user_metrics}\n\n"
                "Optimal daily targets:\n{optimal_targets}\n\n"
                "What was my {focus_metric} on average over {duration_label}?"
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
                "The user wants to compare a specific metric against its optimal "
                "daily target over the period. "
                "State the user's average actual value, the optimal target, and the "
                "delta (how far above or below target they are on average). "
                "Give a one-sentence interpretation of what that gap means. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my daily health metrics for {duration_label}:\n{user_metrics}\n\n"
                "Optimal daily targets:\n{optimal_targets}\n\n"
                "How does my {focus_metric} compare to the optimal target over {duration_label}?"
            ),
        ),
    ]
)

_MULTI_METRIC_DEEP_DIVE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a personal health coach conducting a comprehensive review. "
                "For every metric, provide: the user's average actual value over the "
                "period, the optimal daily target, the gap, and a brief interpretation. "
                "Then close with a short overall assessment and top insight. "
                "Use a structured format with one section per metric. "
                f"{_NULL_METRIC_INSTRUCTION}"
            ),
        ),
        (
            "human",
            (
                "Here are my daily health metrics for {duration_label}:\n{user_metrics}\n\n"
                "Optimal daily targets:\n{optimal_targets}\n\n"
                "Focus metric (if any): {focus_metric}\n\n"
                "Give me a detailed breakdown of all my metrics for {duration_label}."
            ),
        ),
    ]
)

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

PROMPT_REGISTRY: dict[str, ChatPromptTemplate] = {
    "performance_summary":    _PERFORMANCE_SUMMARY,
    "next_period_plan":       _NEXT_PERIOD_PLAN,
    "single_metric_lookup":   _SINGLE_METRIC_LOOKUP,
    "metric_comparison":      _METRIC_COMPARISON,
    "multi_metric_deep_dive": _MULTI_METRIC_DEEP_DIVE,
}
