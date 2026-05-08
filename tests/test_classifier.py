"""
Unit tests for classifier.py.

All DeepSeek HTTP calls are mocked — no real API key or network needed.

Covers:
- Valid single-intent prompt → {valid: true, sub_requests: [one item]}
- Valid compound prompt      → {valid: true, sub_requests: [two items]}
- Off-topic rejection        → {valid: false, reason: str}
- Out-of-range rejection     → {valid: false, reason: str}
- Cross-user rejection       → {valid: false, reason: str}
- Missing API key            → EnvironmentError
- Non-JSON API response      → RuntimeError
- HTTP error from API        → RuntimeError
"""

import json
from unittest.mock import MagicMock, patch

import pytest

import classifier as clf_module
from classifier import classify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response that returns the given body as JSON."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "choices": [
            {"message": {"content": json.dumps(body)}}
        ]
    }
    mock_resp.raise_for_status = MagicMock()  # no-op for 200
    return mock_resp


def _mock_error_response(status_code: int = 500) -> MagicMock:
    """Build a mock requests.Response that raises on raise_for_status."""
    import requests as req_lib
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.side_effect = req_lib.HTTPError(
        f"HTTP {status_code}"
    )
    return mock_resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestClassifyValidSingleIntent:
    def test_returns_valid_true(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": True,
            "reason": None,
            "sub_requests": [
                {"intent": "performance_summary", "focus_metric": None}
            ],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "How did I do last week?")

        assert result["valid"] is True
        assert result["reason"] is None
        assert len(result["sub_requests"]) == 1
        assert result["sub_requests"][0]["intent"] == "performance_summary"

    def test_single_metric_lookup_has_focus_metric(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": True,
            "reason": None,
            "sub_requests": [
                {"intent": "single_metric_lookup", "focus_metric": "sleep"}
            ],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "How long did I sleep on average?")

        assert result["valid"] is True
        assert result["sub_requests"][0]["focus_metric"] == "sleep"


class TestClassifyValidCompoundIntent:
    def test_returns_two_sub_requests(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": True,
            "reason": None,
            "sub_requests": [
                {"intent": "performance_summary", "focus_metric": None},
                {"intent": "next_week_plan", "focus_metric": None},
            ],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "How did I do last week and what's my plan?")

        assert result["valid"] is True
        assert len(result["sub_requests"]) == 2
        intents = [sr["intent"] for sr in result["sub_requests"]]
        assert "performance_summary" in intents
        assert "next_week_plan" in intents

    def test_order_preserved(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": True,
            "reason": None,
            "sub_requests": [
                {"intent": "performance_summary", "focus_metric": None},
                {"intent": "next_week_plan", "focus_metric": None},
            ],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "How did I do and what should I focus on?")

        assert result["sub_requests"][0]["intent"] == "performance_summary"
        assert result["sub_requests"][1]["intent"] == "next_week_plan"


class TestClassifyOffTopicRejection:
    def test_returns_valid_false(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": False,
            "reason": "That question is not related to your health metrics.",
            "sub_requests": [],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "What's the weather like today?")

        assert result["valid"] is False

    def test_reason_is_non_empty_string(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": False,
            "reason": "That question is not related to your health metrics.",
            "sub_requests": [],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "What's the weather like today?")

        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_sub_requests_is_empty(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": False,
            "reason": "Off-topic.",
            "sub_requests": [],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "What's the weather like today?")

        assert result["sub_requests"] == []


class TestClassifyOutOfRangeRejection:
    def test_returns_valid_false_with_reason(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": False,
            "reason": "This app only has data for the current week. Historical data is not available.",
            "sub_requests": [],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "What were my metrics 6 months ago?")

        assert result["valid"] is False
        assert "week" in result["reason"].lower() or "historical" in result["reason"].lower() or result["reason"]


class TestClassifyCrossUserRejection:
    def test_returns_valid_false_with_reason(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        body = {
            "valid": False,
            "reason": "You can only access your own health data.",
            "sub_requests": [],
        }
        with patch("classifier.requests.post", return_value=_mock_response(body)):
            result = classify("1", "How did user 2 do last week?")

        assert result["valid"] is False
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


class TestClassifyErrorHandling:
    def test_missing_api_key_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="DEEPSEEK_API_KEY"):
            classify("1", "How did I do?")

    def test_non_json_response_raises_runtime_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "not valid json {"}}]
        }
        with patch("classifier.requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="non-JSON"):
                classify("1", "How did I do?")

    def test_http_error_raises_runtime_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        with patch(
            "classifier.requests.post",
            return_value=_mock_error_response(500),
        ):
            with pytest.raises(RuntimeError, match="DeepSeek API request failed"):
                classify("1", "How did I do?")
