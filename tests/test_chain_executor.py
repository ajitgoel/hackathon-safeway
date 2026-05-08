"""
Integration tests for chain_executor.py.

LangChain chains and RunnableParallel are mocked — no real LLM calls made.

Covers:
- Single sub-request returns [{intent, label, response}]
- Label includes the duration suffix (e.g. "Performance Summary (Last 7 Days)")
- Data is sliced to the correct duration_days before being passed to the chain
- Multiple sub-requests run via RunnableParallel; results are in input order
- Correct number of chains is passed to RunnableParallel
- Each sub-request uses its own duration_days (compound request)
- Unknown intent raises ValueError before any LLM call
- Missing DEEPSEEK_API_KEY raises EnvironmentError
- Unknown user_id raises KeyError
- Empty sub-requests list returns []
"""

from unittest.mock import MagicMock, call, patch

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


def _mock_llm() -> MagicMock:
    """Return a mock LLM (ChatOpenAI never instantiated)."""
    return MagicMock()


def _make_parallel_mock(key_text_pairs: dict[str, str]) -> MagicMock:
    """Build a mock RunnableParallel whose .invoke() returns AIMessages."""
    mock = MagicMock()
    mock.invoke.return_value = {
        key: _make_ai_message(text) for key, text in key_text_pairs.items()
    }
    return mock


# ---------------------------------------------------------------------------
# Sub-request fixtures — all include duration_days
# ---------------------------------------------------------------------------

SINGLE_7_DAYS = [
    {"intent": "performance_summary", "focus_metric": None, "duration_days": 7},
]

SINGLE_14_DAYS = [
    {"intent": "metric_comparison", "focus_metric": "steps", "duration_days": 14},
]

SINGLE_30_DAYS = [
    {"intent": "multi_metric_deep_dive", "focus_metric": None, "duration_days": 30},
]

COMPOUND_7_AND_30 = [
    {"intent": "performance_summary", "focus_metric": None, "duration_days": 7},
    {"intent": "next_period_plan",    "focus_metric": None, "duration_days": 30},
]

THREE_REQUESTS = [
    {"intent": "performance_summary",  "focus_metric": None,    "duration_days": 7},
    {"intent": "single_metric_lookup", "focus_metric": "sleep", "duration_days": 14},
    {"intent": "next_period_plan",     "focus_metric": None,    "duration_days": 30},
]


# ---------------------------------------------------------------------------
# Single sub-request — basic shape
# ---------------------------------------------------------------------------

class TestSingleSubRequest:
    def test_returns_list_with_one_item(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__performance_summary": "You did great!"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_7_DAYS)
        assert len(results) == 1

    def test_result_has_correct_intent(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__performance_summary": "You did great!"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_7_DAYS)
        assert results[0]["intent"] == "performance_summary"

    def test_result_has_correct_response_text(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__performance_summary": "You did great!"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_7_DAYS)
        assert results[0]["response"] == "You did great!"


# ---------------------------------------------------------------------------
# Label includes duration suffix
# ---------------------------------------------------------------------------

class TestLabelIncludesDuration:
    def test_7_day_label(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__performance_summary": "resp"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_7_DAYS)
        assert results[0]["label"] == "Performance Summary (Last 7 Days)"

    def test_14_day_label(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__metric_comparison": "resp"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_14_DAYS)
        assert results[0]["label"] == "Metric Comparison (Last 14 Days)"

    def test_30_day_label(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock(
            {"0__multi_metric_deep_dive": "resp"}
        )
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", SINGLE_30_DAYS)
        assert results[0]["label"] == "Deep Dive (Last 30 Days)"

    def test_compound_each_block_has_own_duration_label(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock({
            "0__performance_summary": "summary resp",
            "1__next_period_plan":    "plan resp",
        })
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_7_AND_30)
        assert results[0]["label"] == "Performance Summary (Last 7 Days)"
        assert results[1]["label"] == "Next Period Plan (Last 30 Days)"


# ---------------------------------------------------------------------------
# Data slicing — verify the correct number of days is passed to the chain
#
# Strategy: patch RunnableLambda so that when the parallel mock calls
# .invoke({}), the wrapped lambda actually executes and we intercept the
# chain.invoke(captured_input) call to record what was passed.
# ---------------------------------------------------------------------------

class TestDataSlicing:
    def _run_and_capture(self, monkeypatch, sub_requests, parallel_keys):
        """
        Run execute_chains with a mock LLM and capture every captured_input
        dict that gets passed to chain.invoke().

        Returns the list of captured dicts (one per sub-request).
        """
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        chain_inputs: list[dict] = []

        # Build a mock chain whose .invoke() records its argument.
        def make_mock_chain():
            mock_chain = MagicMock()
            def record_invoke(inp):
                chain_inputs.append(inp)
                return _make_ai_message("resp")
            mock_chain.invoke.side_effect = record_invoke
            # prompt | llm  →  mock_chain
            mock_chain.__ror__ = MagicMock(return_value=mock_chain)
            mock_chain.__or__ = MagicMock(return_value=mock_chain)
            return mock_chain

        # Patch PROMPT_REGISTRY so every template's pipe returns our spy chain.
        mock_chain = make_mock_chain()
        mock_template = MagicMock()
        mock_template.__or__ = MagicMock(return_value=mock_chain)

        mock_registry = {intent: mock_template for intent in [
            "performance_summary", "next_period_plan", "single_metric_lookup",
            "metric_comparison", "multi_metric_deep_dive",
        ]}

        # Use a real RunnableParallel so the lambdas actually execute.
        # Each lambda calls chain.invoke(captured_input) which we intercept above.
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "PROMPT_REGISTRY", mock_registry):
            execute_chains("1", sub_requests)

        return chain_inputs

    def test_7_day_slice_passes_7_entries(self, monkeypatch):
        """The chain input for a 7-day request must contain exactly 7 daily entries."""
        import ast
        chain_inputs = self._run_and_capture(
            monkeypatch, SINGLE_7_DAYS, ["0__performance_summary"]
        )
        assert len(chain_inputs) == 1
        sliced = ast.literal_eval(chain_inputs[0]["user_metrics"])
        assert len(sliced) == 7

    def test_7_day_slice_is_the_most_recent_7_entries(self, monkeypatch):
        """The 7-day slice must be the last 7 entries (most recent), not the first."""
        import ast
        from data_store import get_user_metrics as real_get
        expected_slice = real_get("1")[-7:]

        chain_inputs = self._run_and_capture(
            monkeypatch, SINGLE_7_DAYS, ["0__performance_summary"]
        )
        sliced = ast.literal_eval(chain_inputs[0]["user_metrics"])
        assert sliced == expected_slice

    def test_duration_label_in_chain_input(self, monkeypatch):
        """The chain input must contain the correct duration_label string."""
        chain_inputs = self._run_and_capture(
            monkeypatch, SINGLE_7_DAYS, ["0__performance_summary"]
        )
        assert chain_inputs[0]["duration_label"] == "the last 7 days"

    def test_14_day_slice_passes_14_entries(self, monkeypatch):
        """A 14-day request must slice exactly 14 entries."""
        import ast
        chain_inputs = self._run_and_capture(
            monkeypatch, SINGLE_14_DAYS, ["0__metric_comparison"]
        )
        sliced = ast.literal_eval(chain_inputs[0]["user_metrics"])
        assert len(sliced) == 14

    def test_compound_each_sub_request_gets_own_slice(self, monkeypatch):
        """In a compound request, each chain must receive its own duration slice."""
        import ast
        chain_inputs = self._run_and_capture(
            monkeypatch, COMPOUND_7_AND_30,
            ["0__performance_summary", "1__next_period_plan"]
        )
        assert len(chain_inputs) == 2
        slice_0 = ast.literal_eval(chain_inputs[0]["user_metrics"])
        slice_1 = ast.literal_eval(chain_inputs[1]["user_metrics"])
        assert len(slice_0) == 7
        assert len(slice_1) == 30


# ---------------------------------------------------------------------------
# Multiple sub-requests — ordering and chain count
# ---------------------------------------------------------------------------

class TestMultipleSubRequests:
    def test_returns_correct_number_of_results(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock({
            "0__performance_summary": "Summary response",
            "1__next_period_plan":    "Plan response",
        })
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_7_AND_30)
        assert len(results) == 2

    def test_results_are_in_input_order(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock({
            "0__performance_summary": "Summary response",
            "1__next_period_plan":    "Plan response",
        })
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_7_AND_30)
        assert results[0]["intent"] == "performance_summary"
        assert results[1]["intent"] == "next_period_plan"

    def test_correct_number_of_chains_passed_to_parallel(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        captured_kwargs: dict = {}

        def capture_parallel(**kwargs):
            captured_kwargs.update(kwargs)
            return _make_parallel_mock({
                "0__performance_summary": "Summary",
                "1__next_period_plan":    "Plan",
            })

        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", side_effect=capture_parallel):
            execute_chains("1", COMPOUND_7_AND_30)

        assert len(captured_kwargs) == 2

    def test_three_sub_requests_ordering_preserved(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock({
            "0__performance_summary":  "Summary",
            "1__single_metric_lookup": "Sleep was 6.5h",
            "2__next_period_plan":     "Plan",
        })
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", THREE_REQUESTS)
        assert results[0]["intent"] == "performance_summary"
        assert results[1]["intent"] == "single_metric_lookup"
        assert results[2]["intent"] == "next_period_plan"

    def test_response_text_matches_per_intent(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_parallel = _make_parallel_mock({
            "0__performance_summary": "Summary response",
            "1__next_period_plan":    "Plan response",
        })
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()), \
             patch.object(ce_module, "RunnableParallel", return_value=mock_parallel):
            results = execute_chains("1", COMPOUND_7_AND_30)
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
        with pytest.raises(ValueError, match="Unknown intent"):
            execute_chains("1", [
                {"intent": "nonexistent_intent", "focus_metric": None, "duration_days": 7}
            ])

    def test_unknown_intent_raises_before_llm_call(self, monkeypatch):
        """Intent validation must happen before _build_llm is called."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        with patch.object(ce_module, "_build_llm") as mock_build:
            with pytest.raises(ValueError):
                execute_chains("1", [
                    {"intent": "bad_intent", "focus_metric": None, "duration_days": 7}
                ])
            mock_build.assert_not_called()

    def test_missing_api_key_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
            execute_chains("1", SINGLE_7_DAYS)

    def test_unknown_user_raises_key_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        with patch.object(ce_module, "_build_llm", return_value=_mock_llm()):
            with pytest.raises(KeyError):
                execute_chains("999", SINGLE_7_DAYS)
