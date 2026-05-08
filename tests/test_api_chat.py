"""
Integration tests for POST /chat.

The full pipeline (classifier → chain_executor → response_assembler) is tested
with chain_executor mocked so no real LLM calls are made. The classifier is also
mocked to return controlled responses.

Covers:
- Valid single-intent request returns {valid: true, blocks: [one block]}
- Valid compound request returns {valid: true, blocks: [multiple blocks in order]}
- Invalid request returns {valid: false, reason: "..."} without calling chain_executor
- Unknown user_id returns 404
"""

import os
import pytest

# Set the API key before importing api so the startup guard passes
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import api as api_module
from api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_classification(sub_requests: list[dict]) -> dict:
    return {"valid": True, "reason": None, "sub_requests": sub_requests}


def _invalid_classification(reason: str) -> dict:
    return {"valid": False, "reason": reason, "sub_requests": []}


def _chain_results(intents_and_labels: list[tuple[str, str]]) -> list[dict]:
    return [
        {"intent": intent, "label": label, "response": f"Response for {label}"}
        for intent, label in intents_and_labels
    ]


# ---------------------------------------------------------------------------
# Valid single-intent request
# ---------------------------------------------------------------------------

class TestChatValidSingleIntent:
    def test_status_200(self):
        classification = _valid_classification(
            [{"intent": "performance_summary", "focus_metric": None}]
        )
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            response = client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"})

        assert response.status_code == 200

    def test_valid_true_in_response(self):
        classification = _valid_classification(
            [{"intent": "performance_summary", "focus_metric": None}]
        )
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"}).json()

        assert body["valid"] is True

    def test_returns_one_block(self):
        classification = _valid_classification(
            [{"intent": "performance_summary", "focus_metric": None}]
        )
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"}).json()

        assert len(body["blocks"]) == 1

    def test_block_has_label_and_response(self):
        classification = _valid_classification(
            [{"intent": "performance_summary", "focus_metric": None}]
        )
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"}).json()

        block = body["blocks"][0]
        assert "label" in block
        assert "response" in block

    def test_block_label_matches_intent(self):
        classification = _valid_classification(
            [{"intent": "performance_summary", "focus_metric": None}]
        )
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"}).json()

        assert body["blocks"][0]["label"] == "Performance Summary"

    def test_chain_executor_called_with_sub_requests(self):
        sub_requests = [{"intent": "performance_summary", "focus_metric": None}]
        classification = _valid_classification(sub_requests)
        chains = _chain_results([("performance_summary", "Performance Summary")])

        with patch.object(api_module, "classify", return_value=classification) as mock_clf, \
             patch.object(api_module, "execute_chains", return_value=chains) as mock_exec:
            client.post("/chat", json={"user_id": "1", "prompt": "How did I do?"})

        mock_exec.assert_called_once_with("1", sub_requests)


# ---------------------------------------------------------------------------
# Valid compound request
# ---------------------------------------------------------------------------

class TestChatValidCompoundIntent:
    def test_returns_multiple_blocks(self):
        classification = _valid_classification([
            {"intent": "performance_summary", "focus_metric": None},
            {"intent": "next_week_plan", "focus_metric": None},
        ])
        chains = _chain_results([
            ("performance_summary", "Performance Summary"),
            ("next_week_plan", "Next Week Plan"),
        ])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do and what's my plan?"}).json()

        assert len(body["blocks"]) == 2

    def test_blocks_in_correct_order(self):
        classification = _valid_classification([
            {"intent": "performance_summary", "focus_metric": None},
            {"intent": "next_week_plan", "focus_metric": None},
        ])
        chains = _chain_results([
            ("performance_summary", "Performance Summary"),
            ("next_week_plan", "Next Week Plan"),
        ])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do and what's my plan?"}).json()

        assert body["blocks"][0]["label"] == "Performance Summary"
        assert body["blocks"][1]["label"] == "Next Week Plan"

    def test_valid_true_for_compound(self):
        classification = _valid_classification([
            {"intent": "performance_summary", "focus_metric": None},
            {"intent": "next_week_plan", "focus_metric": None},
        ])
        chains = _chain_results([
            ("performance_summary", "Performance Summary"),
            ("next_week_plan", "Next Week Plan"),
        ])

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains", return_value=chains):
            body = client.post("/chat", json={"user_id": "1", "prompt": "How did I do and what's my plan?"}).json()

        assert body["valid"] is True


# ---------------------------------------------------------------------------
# Invalid request — classifier rejects
# ---------------------------------------------------------------------------

class TestChatInvalidRequest:
    def test_status_200_for_invalid_prompt(self):
        """Invalid prompts still return 200 — rejection is in the body."""
        classification = _invalid_classification("That question is off-topic.")

        with patch.object(api_module, "classify", return_value=classification):
            response = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"})

        assert response.status_code == 200

    def test_valid_false_in_response(self):
        classification = _invalid_classification("That question is off-topic.")

        with patch.object(api_module, "classify", return_value=classification):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()

        assert body["valid"] is False

    def test_reason_present_in_response(self):
        classification = _invalid_classification("That question is off-topic.")

        with patch.object(api_module, "classify", return_value=classification):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()

        assert body["reason"] == "That question is off-topic."

    def test_chain_executor_not_called_for_invalid(self):
        """chain_executor must NOT be called when the classifier rejects."""
        classification = _invalid_classification("Off-topic.")

        with patch.object(api_module, "classify", return_value=classification), \
             patch.object(api_module, "execute_chains") as mock_exec:
            client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"})

        mock_exec.assert_not_called()

    def test_no_blocks_key_for_invalid(self):
        classification = _invalid_classification("Off-topic.")

        with patch.object(api_module, "classify", return_value=classification):
            body = client.post("/chat", json={"user_id": "1", "prompt": "What's the weather?"}).json()

        assert "blocks" not in body


# ---------------------------------------------------------------------------
# Unknown user_id → 404
# ---------------------------------------------------------------------------

class TestChatUnknownUser:
    def test_status_404_for_unknown_user(self):
        response = client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        assert response.status_code == 404

    def test_error_body_for_unknown_user(self):
        response = client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})
        assert response.json() == {"error": "User not found"}

    def test_classifier_not_called_for_unknown_user(self):
        """Classifier must NOT be called when the user doesn't exist."""
        with patch.object(api_module, "classify") as mock_clf:
            client.post("/chat", json={"user_id": "999", "prompt": "How did I do?"})

        mock_clf.assert_not_called()
