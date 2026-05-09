"""
Integration tests for GET /metrics/{user_id}.

Uses FastAPI's TestClient (backed by httpx) — no live server required.

Covers:
- 200 with a list of 30 daily metric dicts for a known user
- 404 with {"error": "User not found"} for an unknown user
- Null metric values serialised as JSON null (not omitted)
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure the API key guard passes before importing the app.
os.environ.setdefault("GROQ_API_KEY", "test-key")

from api import app  # noqa: E402

METRIC_KEYS = {"sleep", "steps", "resting_hr", "water", "workouts", "hrv"}
DAY_KEYS = METRIC_KEYS | {"date"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestGetMetricsKnownUser:
    def test_status_200_for_known_user(self, client):
        response = client.get("/metrics/1")
        assert response.status_code == 200

    def test_response_is_a_list(self, client):
        response = client.get("/metrics/1")
        assert isinstance(response.json(), list)

    def test_response_contains_30_entries(self, client):
        response = client.get("/metrics/1")
        assert len(response.json()) == 30

    def test_each_entry_has_all_keys(self, client):
        entries = client.get("/metrics/1").json()
        for day in entries:
            assert set(day.keys()) == DAY_KEYS, f"Missing keys on {day.get('date')}"

    def test_entries_have_date_strings(self, client):
        entries = client.get("/metrics/1").json()
        for day in entries:
            assert isinstance(day["date"], str)
            assert len(day["date"]) == 10  # YYYY-MM-DD

    def test_entries_ordered_oldest_first(self, client):
        entries = client.get("/metrics/1").json()
        dates = [day["date"] for day in entries]
        assert dates == sorted(dates)

    def test_null_hrv_serialised_as_json_null_not_omitted(self, client):
        """User 1 has hrv=None on some days — must appear as null in JSON."""
        entries = client.get("/metrics/1").json()
        null_hrv_days = [day for day in entries if day["hrv"] is None]
        assert len(null_hrv_days) > 0, "Expected at least one day with hrv=null"
        for day in null_hrv_days:
            assert "hrv" in day  # key must be present, not omitted

    def test_null_sleep_for_user_3(self, client):
        """User 3 has sleep=None on some days — must appear as null."""
        entries = client.get("/metrics/3").json()
        null_sleep_days = [day for day in entries if day["sleep"] is None]
        assert len(null_sleep_days) > 0, "Expected at least one day with sleep=null"
        for day in null_sleep_days:
            assert "sleep" in day

    def test_all_metrics_non_null_for_user_2(self, client):
        """User 2 has all metrics logged — no null values expected."""
        entries = client.get("/metrics/2").json()
        for day in entries:
            for key in METRIC_KEYS:
                assert day[key] is not None, f"User 2 day {day['date']} has null {key}"

    def test_content_type_is_json(self, client):
        response = client.get("/metrics/1")
        assert "application/json" in response.headers["content-type"]

    def test_all_three_users_return_30_entries(self, client):
        for uid in ("1", "2", "3"):
            response = client.get(f"/metrics/{uid}")
            assert response.status_code == 200
            assert len(response.json()) == 30


class TestGetMetricsUnknownUser:
    def test_status_404_for_unknown_user(self, client):
        response = client.get("/metrics/999")
        assert response.status_code == 404

    def test_error_body_for_unknown_user(self, client):
        response = client.get("/metrics/999")
        assert response.json() == {"error": "User not found"}

    def test_status_404_for_string_unknown_user(self, client):
        response = client.get("/metrics/unknown")
        assert response.status_code == 404

    def test_error_body_for_string_unknown_user(self, client):
        response = client.get("/metrics/unknown")
        assert response.json() == {"error": "User not found"}
