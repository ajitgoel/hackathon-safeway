"""
Integration tests for POST /chat and POST /chat/stream.

The full pipeline (classifier → chain_executor → response_assembler) is tested
with classifier and chain_executor mocked so no real LLM calls are made.

Both classify() and execute_chains() are now async, so patches use AsyncMock.

Covers:
- Valid single-intent request returns {valid: true, blocks: [one block]}
- Valid compound request returns {valid: true, blocks: [multiple blocks in order]}
- Invalid request returns {valid: false, reason: "..."} without calling chain_executor
- Unknown user_id returns 404
- classifier is not called for an unknown user_id
- chain_executor is not called for an invalid prompt
- chain_executor receives the correct user_id and sub_requests
- /chat/stream returns SSE text/event-stream for valid requests
- /chat/stream returns SSE rejection event for invalid prompts
"""

import os

# Set the API key before importing api so the startup guard passes.
os.environ.setdefault("GROQ_API_KEY", "test-key")

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

import api as api_module
from api import app


# ---------------------------------------------------------------------------
# Shared client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_classification(sub_requests: list[dict]) -> dict:
    return {"valid": True, "reason": None, "sub_requests": sub_requests}


def _invalid_classification(reason: str) -> dict:
    return {"valid": False, "reason": reason, "sub_requests": []}


def _chain_results(items: list[tuple[str, str]]) -> list[dict]:
    """Build a chain_executor return value from (intent, label) pairs."""
    return [
        {"intent": intent, "label": label, "response": f"Response for {label}"}
        for intent, label in items
    ]


# ---------------------------------------------------------------------------
# Valid single-intent request
# ---------------------------------------------------------------------------

class TestChatValidSingleIntent:
    _sub_requests = [
        {"intent": "performance_summary", "focus_metric": None, "duration_days": 7}
    ]
    _chains = _chain_results([
        ("performance_summary", "Performance Summary (Last 7 Days)")
    ])

    def test_status_200(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            response = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"})
        assert response.status_code == 200

    def test_valid_true_in_response(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        assert body["valid"] is True

    def test_returns_one_block(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        assert len(body["blocks"]) == 1

    def test_block_has_label_and_response_keys(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        block = body["blocks"][0]
        assert "label" in block
        assert "response" in block

    def test_block_label_matches_chain_result(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        assert body["blocks"][0]["label"] == "Performance Summary (Last 7 Days)"

    def test_block_response_matches_chain_result(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        assert body["blocks"][0]["response"] == "Response for Performance Summary (Last 7 Days)"

    def test_no_reason_key_for_valid_response(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"}).json()
        assert "reason" not in body

    def test_chain_executor_called_with_correct_args(self, client):
        mock_exec = AsyncMock(return_value=self._chains)
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=mock_exec):
            client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week?"})
        mock_exec.assert_called_once_with("1", self._sub_requests)


# ---------------------------------------------------------------------------
# Valid compound request — two sub-requests with different durations
# ---------------------------------------------------------------------------

class TestChatValidCompoundIntent:
    _sub_requests = [
        {"intent": "performance_summary", "focus_metric": None, "duration_days": 7},
        {"intent": "next_period_plan",    "focus_metric": None, "duration_days": 30},
    ]
    _chains = _chain_results([
        ("performance_summary", "Performance Summary (Last 7 Days)"),
        ("next_period_plan",    "Next Period Plan (Last 30 Days)"),
    ])

    def test_returns_two_blocks(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week and what's my plan?"}).json()
        assert len(body["blocks"]) == 2

    def test_blocks_in_correct_order(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week and what's my plan?"}).json()
        assert body["blocks"][0]["label"] == "Performance Summary (Last 7 Days)"
        assert body["blocks"][1]["label"] == "Next Period Plan (Last 30 Days)"

    def test_valid_true_for_compound(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week and what's my plan?"}).json()
        assert body["valid"] is True

    def test_each_block_has_label_and_response(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week and what's my plan?"}).json()
        for block in body["blocks"]:
            assert "label" in block
            assert "response" in block

    def test_chain_executor_called_with_both_sub_requests(self, client):
        mock_exec = AsyncMock(return_value=self._chains)
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=mock_exec):
            client.post("/chat", json={"user_id": "1", "prompt": "How did I do last week and what's my plan?"})
        mock_exec.assert_called_once_with("1", self._sub_requests)


# ---------------------------------------------------------------------------
# Invalid request — classifier rejects
# ---------------------------------------------------------------------------

class TestChatInvalidRequest:
    def test_status_200_for_invalid_prompt(self, client):
        """Rejected prompts still return HTTP 200 — rejection is in the body."""
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("That question is off-topic."))):
            response = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"})
        assert response.status_code == 200

    def test_valid_false_in_response(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("That question is off-topic."))):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()
        assert body["valid"] is False

    def test_reason_present_and_correct(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("That question is off-topic."))):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()
        assert body["reason"] == "That question is off-topic."

    def test_no_blocks_key_for_invalid(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("Off-topic."))):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()
        assert "blocks" not in body

    def test_chain_executor_not_called_for_invalid(self, client):
        """chain_executor must NOT be called when the classifier rejects."""
        mock_exec = AsyncMock()
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("Off-topic."))), \
             patch.object(api_module, "execute_chains", new=mock_exec):
            client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"})
        mock_exec.assert_not_called()

    def test_out_of_range_rejection(self, client):
        reason = "This app only supports data from the last 30 days."
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification(reason))):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What were my metrics 6 months ago?"}).json()
        assert body["valid"] is False
        assert body["reason"] == reason

    def test_cross_user_rejection(self, client):
        reason = "You can only access your own health data."
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification(reason))):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did user 2 do?"}).json()
        assert body["valid"] is False
        assert body["reason"] == reason


# ---------------------------------------------------------------------------
# Unknown user_id → 404
# ---------------------------------------------------------------------------

class TestChatUnknownUser:
    def test_status_404_for_unknown_user(self, client):
        response = client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        assert response.status_code == 404

    def test_error_body_for_unknown_user(self, client):
        response = client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        assert response.json() == {"error": "User not found"}

    def test_classifier_not_called_for_unknown_user(self, client):
        """Classifier must NOT be called when the user doesn't exist."""
        mock_clf = AsyncMock()
        with patch.object(api_module, "classify", new=mock_clf):
            client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        mock_clf.assert_not_called()

    def test_chain_executor_not_called_for_unknown_user(self, client):
        """chain_executor must NOT be called when the user doesn't exist."""
        mock_exec = AsyncMock()
        with patch.object(api_module, "execute_chains", new=mock_exec):
            client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        mock_exec.assert_not_called()


# ---------------------------------------------------------------------------
# POST /chat/stream — SSE endpoint
# ---------------------------------------------------------------------------

class TestChatStream:
    _sub_requests = [
        {"intent": "performance_summary", "focus_metric": None, "duration_days": 7}
    ]
    _chains = _chain_results([
        ("performance_summary", "Performance Summary (Last 7 Days)")
    ])

    def test_stream_returns_200(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            response = client.post("/chat/stream", json={"user_id": "1", "prompt": "How did I do last week?"})
        assert response.status_code == 200

    def test_stream_content_type_is_event_stream(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            response = client.post("/chat/stream", json={"user_id": "1", "prompt": "How did I do last week?"})
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_contains_done_sentinel(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_valid_classification(self._sub_requests))), \
             patch.object(api_module, "execute_chains", new=AsyncMock(return_value=self._chains)):
            response = client.post("/chat/stream", json={"user_id": "1", "prompt": "How did I do last week?"})
        assert "[DONE]" in response.text

    def test_stream_invalid_prompt_contains_invalid_marker(self, client):
        with patch.object(api_module, "classify", new=AsyncMock(return_value=_invalid_classification("Off-topic."))):
            response = client.post("/chat/stream", json={"user_id": "1", "prompt": "What's the weather?"})
        assert "INVALID" in response.text

    def test_stream_unknown_user_returns_404(self, client):
        response = client.post("/chat/stream", json={"user_id": "999", "prompt": "How did I do?"})
        assert response.status_code == 404
