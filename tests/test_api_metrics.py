"""
Integration tests for GET /metrics/{user_id}.

Uses FastAPI's TestClient (backed by httpx) — no live server required.

Covers:
- 200 with correct metrics dict for a known user
- 404 with {"error": "User not found"} for an unknown user
- Null metric values serialised as JSON null (not omitted)
"""

import json
import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

EXPECTED_METRIC_KEYS = {"sleep", "steps", "resting_hr", "water", "workouts", "hrv"}


class TestGetMetricsKnownUser:
    def test_status_200_for_known_user(self):
        response = client.get("/metrics/1")
        assert response.status_code == 200

    def test_response_contains_all_metric_keys(self):
        response = client.get("/metrics/1")
        body = response.json()
        assert set(body.keys()) == EXPECTED_METRIC_KEYS

    def test_correct_values_for_user_1(self):
        response = client.get("/metrics/1")
        body = response.json()
        assert body["sleep"] == 6.5
        assert body["steps"] == 8200
        assert body["resting_hr"] == 72
        assert body["water"] == 1.8
        assert body["workouts"] == 3

    def test_null_metric_serialised_as_json_null_not_omitted(self):
        """User 1 has hrv=None — must appear as null in JSON, not be absent."""
        response = client.get("/metrics/1")
        # Check the raw JSON text to confirm 'null' is present, not the key missing
        assert "hrv" in response.json()
        assert response.json()["hrv"] is None
        assert '"hrv": null' in response.text or '"hrv":null' in response.text

    def test_null_sleep_for_user_3(self):
        """User 3 has sleep=None — must appear as null."""
        response = client.get("/metrics/3")
        body = response.json()
        assert "sleep" in body
        assert body["sleep"] is None

    def test_all_metrics_present_for_user_2(self):
        """User 2 has all metrics logged — none should be null."""
        response = client.get("/metrics/2")
        body = response.json()
        assert set(body.keys()) == EXPECTED_METRIC_KEYS
        assert all(v is not None for v in body.values())

    def test_content_type_is_json(self):
        response = client.get("/metrics/1")
        assert "application/json" in response.headers["content-type"]


class TestGetMetricsUnknownUser:
    def test_status_404_for_unknown_user(self):
        response = client.get("/metrics/999")
        assert response.status_code == 404

    def test_error_body_for_unknown_user(self):
        response = client.get("/metrics/999")
        assert response.json() == {"error": "User not found"}

    def test_status_404_for_string_unknown_user(self):
        response = client.get("/metrics/unknown")
        assert response.status_code == 404

    def test_error_body_for_string_unknown_user(self):
        response = client.get("/metrics/unknown")
        assert response.json() == {"error": "User not found"}
