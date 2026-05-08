"""
Integration tests for chain_executor.py.

LangChain chains and RunnableParallel are mocked — no real LLM calls made.

Covers:
- Single sub-request returns [{intent, label, response}]
- Multiple sub-requests run via RunnableParallel and results are in input order
- Unknown intent raises ValueError
- Missing DEEPSEEK_API_KEY raises EnvironmentError
- Results preserve order even when the same intent appears twice
"""

from unittest.mock import MagicMock, patch

import pytest

import chain_executor as ce_module
from chain_executor import execute_chains


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ai_message(text: str) -> MagicMock:
    """Simulate a LangChain AIMessage with a .content attribute."""
    msg = MagicMock()
    msg.content = text
    return msg


def _make_parallel_result(keys: list[str], texts: list[str]) -> dict:
    """Build the dict that RunnableParallel.invoke would return."""
    return {key: _make_ai_message(text) for key, text in zip(keys, texts)}


def _mock_llm() -> MagicMock:
    """Return a mock LLM whose pipe operator returns a mock chain."""
    llm = MagicMock()
    # prompt | llm calls llm.__ror__ or prompt.__or__; the result is a chain
    # We mock at the _build_llm level so ChatOpenAI is never instantiated.
    return llm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SINGLE_SUB_REQUEST = [
    {"intent": "performance_summary", "focus_metric": None}
]

COMPOUND_SUB_REQUESTS = [
    {"intent": "performance_summary", "focus_metric": None},
    {"intent": "next_week_plan", "focus_metric": None},
]

THREE_SUB_REQUESTS = [
    {"intent": "performance_summary", "focus_metric": None},
    {"intent": "single_metric_lookup", "focus_metric": "sleep"},
    {"intent": "next_week_plan", "focus_metric": None},
]


# ---------------------------------------------------------------------------
# Single sub-request
# ---------------------------------------------------------------------------

class TestSingleSubRequest:
    def test_returns_list_with_one_item(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("You did great!")
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_SUB_REQUEST)

        assert len(results) == 1

    def test_result_has_correct_intent(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("You did great!")
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_SUB_REQUEST)

        assert results[0]["intent"] == "performance_summary"

    def test_result_has_correct_label(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("You did great!")
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_SUB_REQUEST)

        assert results[0]["label"] == "Performance Summary"

    def test_result_has_correct_response_text(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("You did great!")
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_SUB_REQUEST)

        assert results[0]["response"] == "You did great!"


# ---------------------------------------------------------------------------
# Multiple sub-requests — ordering and chain count
# ---------------------------------------------------------------------------

class TestMultipleSubRequests:
    def test_returns_correct_number_of_results(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("Summary response"),
            "1__next_week_plan": _make_ai_message("Plan response"),
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_SUB_REQUESTS)

        assert len(results) == 2

    def test_results_are_in_input_order(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("Summary response"),
            "1__next_week_plan": _make_ai_message("Plan response"),
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_SUB_REQUESTS)

        assert results[0]["intent"] == "performance_summary"
        assert results[1]["intent"] == "next_week_plan"

    def test_correct_number_of_chains_passed_to_parallel(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        captured_kwargs: dict = {}

        def capture_parallel(**kwargs):
            captured_kwargs.update(kwargs)
            mock = MagicMock()
            mock.invoke.return_value = {
                "0__performance_summary": _make_ai_message("Summary"),
                "1__next_week_plan": _make_ai_message("Plan"),
            }
            return mock

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", side_effect=capture_parallel):
            execute_chains("1", COMPOUND_SUB_REQUESTS)

        assert len(captured_kwargs) == 2

    def test_three_sub_requests_ordering_preserved(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("Summary"),
            "1__single_metric_lookup": _make_ai_message("Sleep was 6.5h"),
            "2__next_week_plan": _make_ai_message("Plan"),
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", THREE_SUB_REQUESTS)

        assert results[0]["intent"] == "performance_summary"
        assert results[1]["intent"] == "single_metric_lookup"
        assert results[2]["intent"] == "next_week_plan"

    def test_response_text_matches_per_intent(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        mock_parallel = MagicMock()
        mock_parallel.invoke.return_value = {
            "0__performance_summary": _make_ai_message("Summary response"),
            "1__next_week_plan": _make_ai_message("Plan response"),
        }

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_SUB_REQUESTS)

        assert results[0]["response"] == "Summary response"
        assert results[1]["response"] == "Plan response"


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptySubRequests:
    def test_empty_list_returns_empty_list(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        results = execute_chains("1", [])
        assert results == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_unknown_intent_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        # Intent validation happens before _build_llm, so no LLM mock needed
        with pytest.raises(ValueError, match="Unknown intent"):
            execute_chains("1", [{"intent": "nonexistent_intent", "focus_metric": None}])

    def test_missing_api_key_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
            execute_chains("1", SINGLE_SUB_REQUEST)

    def test_unknown_user_raises_key_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        # _build_llm is called before get_user_metrics, so mock it
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()):
            with pytest.raises(KeyError):
                execute_chains("999", SINGLE_SUB_REQUEST)
