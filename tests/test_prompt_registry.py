"""
Unit tests for prompt_registry.py.

Tests check observable behaviour only — that templates exist, accept the
correct input variables, format without error, and include null-metric
handling instructions. No LLM calls are made.

Covers:
- Registry contains all 5 intent keys
- Each template accepts user_metrics, optimal_targets, focus_metric
- Each template formats to a non-empty string without raising
- Each formatted prompt contains the null-metric acknowledgement instruction
- single_metric_lookup and metric_comparison use focus_metric in the human turn
- INTENT_LABELS contains a label for every registry key
"""

import pytest
from langchain_core.prompts import ChatPromptTemplate

from prompt_registry import PROMPT_REGISTRY, INTENT_LABELS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = str(
    {
        "sleep": 6.5,
        "steps": 8200,
        "resting_hr": 72,
        "water": 1.8,
        "workouts": 3,
        "hrv": None,
    }
)

SAMPLE_TARGETS = str(
    {
        "sleep": 8.0,
        "steps": 10000,
        "resting_hr": 60,
        "water": 2.5,
        "workouts": 5,
        "hrv": 60,
    }
)

ALL_INTENTS = [
    "performance_summary",
    "next_week_plan",
    "single_metric_lookup",
    "metric_comparison",
    "multi_metric_deep_dive",
]

FOCUS_METRIC_INTENTS = {"single_metric_lookup", "metric_comparison"}


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

    def test_intent_labels_covers_all_intents(self):
        assert set(INTENT_LABELS.keys()) == set(ALL_INTENTS)

    def test_all_labels_are_non_empty_strings(self):
        for intent, label in INTENT_LABELS.items():
            assert isinstance(label, str) and len(label) > 0, (
                f"Label for {intent} is empty"
            )


# ---------------------------------------------------------------------------
# Input variables
# ---------------------------------------------------------------------------

class TestTemplateInputVariables:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_user_metrics_variable(self, intent):
        template = PROMPT_REGISTRY[intent]
        assert "user_metrics" in template.input_variables

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_optimal_targets_variable(self, intent):
        template = PROMPT_REGISTRY[intent]
        assert "optimal_targets" in template.input_variables

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_has_focus_metric_variable(self, intent):
        template = PROMPT_REGISTRY[intent]
        assert "focus_metric" in template.input_variables


# ---------------------------------------------------------------------------
# Formatting (no LLM — just template rendering)
# ---------------------------------------------------------------------------

class TestTemplateFormatting:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_template_formats_without_error(self, intent):
        template = PROMPT_REGISTRY[intent]
        messages = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="sleep",
        )
        assert len(messages) > 0

    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_formatted_output_is_non_empty(self, intent):
        template = PROMPT_REGISTRY[intent]
        messages = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="steps",
        )
        full_text = " ".join(m.content for m in messages)
        assert len(full_text.strip()) > 0


# ---------------------------------------------------------------------------
# Null-metric instruction present in every template
# ---------------------------------------------------------------------------

class TestNullMetricInstruction:
    @pytest.mark.parametrize("intent", ALL_INTENTS)
    def test_system_prompt_mentions_null_handling(self, intent):
        """Every template must instruct the LLM to acknowledge missing metrics."""
        template = PROMPT_REGISTRY[intent]
        messages = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="hrv",
        )
        system_content = messages[0].content.lower()
        # Check for key phrases from the null-metric instruction
        assert "none" in system_content or "missing" in system_content or "didn't log" in system_content or "acknowledge" in system_content


# ---------------------------------------------------------------------------
# focus_metric used meaningfully in relevant templates
# ---------------------------------------------------------------------------

class TestFocusMetricUsage:
    @pytest.mark.parametrize("intent", ["single_metric_lookup", "metric_comparison"])
    def test_focus_metric_appears_in_human_message(self, intent):
        template = PROMPT_REGISTRY[intent]
        messages = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="resting_hr",
        )
        # The human turn (last message) should contain the focus metric value
        human_content = messages[-1].content
        assert "resting_hr" in human_content

    @pytest.mark.parametrize("intent", ["single_metric_lookup", "metric_comparison"])
    def test_different_focus_metrics_produce_different_prompts(self, intent):
        template = PROMPT_REGISTRY[intent]
        msgs_sleep = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="sleep",
        )
        msgs_steps = template.format_messages(
            user_metrics=SAMPLE_METRICS,
            optimal_targets=SAMPLE_TARGETS,
            focus_metric="steps",
        )
        assert msgs_sleep[-1].content != msgs_steps[-1].content
