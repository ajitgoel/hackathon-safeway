"""
Unit tests for prompt_registry.py.

Tests check observable behaviour only — that templates exist, accept the
correct input variables, format without error, and include null-metric
handling instructions. No LLM calls are made.

Covers:
- Registry contains all 5 intent keys
- Each template accepts user_metrics, optimal_targets, focus_metric, duration_label
- Each template formats to a non-empty string without raising
- Each formatted prompt contains the null-metric acknowledgement instruction
- All templates reference duration_label so responses are scoped to the period
- single_metric_lookup and metric_comparison use focus_metric in the human turn
- INTENT_LABEL_TEMPLATES contains a label for every registry key
"""

import pytest
from langchain_core.prompts import ChatPromptTemplate

from prompt_registry import PROMPT_REGISTRY, INTENT_LABEL_TEMPLATES

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_METRICS = str(
    [
        {"date": "2026-05-02", "sleep": 6.5, "steps": 8200, "resting_hr": 72,
         "water": 1.8, "workouts": 1, "hrv": None},
        {"date": "2026-05-03", "sleep": 7.0, "steps": 9100, "resting_hr": 69,
         "water": 2.1, "workouts": 0, "hrv": 55},
        {"date": "2026-05-04", "sleep": 7.5, "steps": 10200, "resting_hr": 66,
         "water": 2.3, "workouts": 1, "hrv": 58},
    ]
)

SAMPLE_TARGETS = str(
    {
        "sleep": 8.0,
        "steps": 10000,
        "resting_hr": 60,
        "water": 2.5,
        "workouts": 1,
        "hrv": 60,
    }
)

SAMPLE_DURATION_LABEL = "the last 7 days"

ALL_INTENTS = [
    "performance_summary",
    "next_period_plan",
    "single_metric_lookup",
    "metric_comparison",
    "multi_metric_deep_dive",
]


# ---------------------------------------------------------------------------
# Registry structure
# ---------------------------------------------------------------------------

class TestRegistryStructure:
    def test_contains_all_five_intents(self):
        assert set(PROMPT_REGISTRY.keys()) == set(ALL_INTENTS)

    def test_all_values_are_chat_prompt_templates(self):
        for intent, template in PROMPT_REGISTRY.items():
            assert isinstance(template, ChatPromptTemplate), (
                f"{intent} is not a ChatPromptTemplate"
            )

    def test_intent_label_templates_covers_all_intents(self):
        assert set(INTENT_LABEL_TEMPLATES.keys()) == set(ALL_INTENTS)

    def test_all_labels_are_non_empty_strings(self):
        for intent, label in INTENT_LABEL_TEMPLATES.items():
            assert isinstance(label, str) and len(label) > 0, (
                f"Label for {intent} is empty"
            )


# ---------------------------------------------------------------------------
# Input variables
# ---------------------------------------------------------------------------

class TestTemplateInputVariables:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_user_metrics_variable(self, intent):
        assert "user_metrics" in PROMPT_REGISTRY[intent].input_variables

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_optimal_targets_variable(self, intent):
        assert "optimal_targets" in PROMPT_REGISTRY[intent].input_variables

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_focus_metric_variable(self, intent):
        assert "focus_metric" in PROMPT_REGISTRY[intent].input_variables

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_duration_label_variable(self, intent):
        assert "duration_label" in PROMPT_REGISTRY[intent].input_variables


# ---------------------------------------------------------------------------
# Formatting (no LLM — just template rendering)
# ---------------------------------------------------------------------------

class TestTemplateFormatting:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_formats_without_error(self, intent):
        messages = PROMPT_REGISTRY[intent].format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="sleep",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        assert len(messages) > 0

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_formatted_output_is_non_empty(self, intent):
        messages = PROMPT_REGISTRY[intent].format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="steps",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        full_text = " ".join(m.content for m in messages)
        assert len(full_text.strip()) > 0

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_duration_label_appears_in_formatted_output(self, intent):
        """Every template must reference duration_label so the LLM knows the period."""
        messages = PROMPT_REGISTRY[intent].format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="sleep",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        full_text = " ".join(m.content for m in messages)
        assert SAMPLE_DURATION_LABEL in full_text, (
            f"{intent} template does not include duration_label in formatted output"
        )

    @pytest.mark.parametrize("duration_label", ["the last 7 days", "the last 14 days", "the last 30 days"])
    def test_different_duration_labels_produce_different_prompts(self, duration_label):
        """Changing duration_label must change the rendered prompt."""
        template = PROMPT_REGISTRY["performance_summary"]
        msgs_a = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric=None,
            duration_label="the last 7 days",
        )
        msgs_b = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric=None,
            duration_label="the last 30 days",
        )
        text_a = " ".join(m.content for m in msgs_a)
        text_b = " ".join(m.content for m in msgs_b)
        assert text_a != text_b


# ---------------------------------------------------------------------------
# Null-metric instruction present in every template
# ---------------------------------------------------------------------------

class TestNullMetricInstruction:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_system_prompt_mentions_null_handling(self, intent):
        """Every template must instruct the LLM to acknowledge missing metrics."""
        messages = PROMPT_REGISTRY[intent].format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="hrv",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        system_content = messages[0].content.lower()
        assert any(
            phrase in system_content
            for phrase in ("none", "missing", "didn't log", "acknowledge", "not log")
        ), f"{intent} system prompt does not mention null/missing metric handling"


# ---------------------------------------------------------------------------
# focus_metric used meaningfully in relevant templates
# ---------------------------------------------------------------------------

class TestFocusMetricUsage:
    @pytest.mark.parametrize("intent", ["single_metric_lookup", "metric_comparison"])
    def test_focus_metric_appears_in_human_message(self, intent):
        messages = PROMPT_REGISTRY[intent].format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="resting_hr",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        human_content = messages[-1].content
        assert "resting_hr" in human_content

    @pytest.mark.parametrize("intent", ["single_metric_lookup", "metric_comparison"])
    def test_different_focus_metrics_produce_different_prompts(self, intent):
        template = PROMPT_REGISTRY[intent]
        msgs_sleep = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="sleep",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        msgs_steps = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="steps",
            duration_label=SAMPLE_DURATION_LABEL,
        )
        assert msgs_sleep[-1].content != msgs_steps[-1].content
