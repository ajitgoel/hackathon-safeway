"""
Unit tests for data_store.py.

Tests cover:
- Known user returns a 30-entry list with all required keys per day
- Unknown user raises KeyError
- Users with null metrics return None (not a missing key)
- get_optimal_targets returns a complete dict for all 6 metrics
- Returned data is a copy — mutations do not affect internal state
"""

import pytest
from data_store import get_user_metrics, get_optimal_targets

METRIC_KEYS = {"sleep", "steps", "resting_hr", "water", "workouts", "hrv"}
DAY_KEYS = METRIC_KEYS | {"date"}


class TestGetUserMetrics:
    def test_known_user_returns_30_entries(self):
        entries = get_user_metrics("1")
        assert len(entries) == 30

    def test_each_entry_has_all_keys(self):
        entries = get_user_metrics("1")
        for day in entries:
            assert set(day.keys()) == DAY_KEYS, f"Missing keys on {day.get('date')}"

    def test_entries_have_date_strings(self):
        entries = get_user_metrics("1")
        for day in entries:
            assert isinstance(day["date"], str)
            # Basic ISO date format check: YYYY-MM-DD
            assert len(day["date"]) == 10
            assert day["date"][4] == "-" and day["date"][7] == "-"

    def test_entries_ordered_oldest_first(self):
        entries = get_user_metrics("1")
        dates = [day["date"] for day in entries]
        assert dates == sorted(dates), "Entries should be ordered oldest-first"

    def test_user1_has_null_hrv_on_some_days(self):
        """User 1 has HRV unlogged on several days — key must be present as None."""
        entries = get_user_metrics("1")
        null_hrv_days = [day for day in entries if day["hrv"] is None]
        assert len(null_hrv_days) > 0, "User 1 should have at least one day with hrv=None"
        for day in null_hrv_days:
            assert "hrv" in day  # key must exist, not be omitted

    def test_user3_has_null_sleep_on_some_days(self):
        """User 3 has sleep unlogged on several days — key must be present as None."""
        entries = get_user_metrics("3")
        null_sleep_days = [day for day in entries if day["sleep"] is None]
        assert len(null_sleep_days) > 0, "User 3 should have at least one day with sleep=None"
        for day in null_sleep_days:
            assert "sleep" in day  # key must exist, not be omitted

    def test_user2_all_metrics_logged(self):
        """User 2 is a high performer — no None values expected."""
        entries = get_user_metrics("2")
        for day in entries:
            for key in METRIC_KEYS:
                assert day[key] is not None, f"User 2 day {day['date']} has None for {key}"

    def test_unknown_user_raises_key_error(self):
        with pytest.raises(KeyError):
            get_user_metrics("999")

    def test_unknown_user_string_id_raises_key_error(self):
        with pytest.raises(KeyError):
            get_user_metrics("unknown")

    def test_numeric_string_user_id_not_int(self):
        """user_id is always a string — passing an int should raise KeyError."""
        with pytest.raises((KeyError, TypeError)):
            get_user_metrics(1)  # type: ignore[arg-type]

    def test_returns_copy_not_reference(self):
        """Mutating the returned list must not affect the internal store."""
        entries = get_user_metrics("1")
        original_sleep = entries[0]["sleep"]
        entries[0]["sleep"] = 999
        fresh = get_user_metrics("1")
        assert fresh[0]["sleep"] == original_sleep

    def test_at_least_three_users_exist(self):
        """Issue 1 requires at least 3 hardcoded users."""
        for uid in ("1", "2", "3"):
            entries = get_user_metrics(uid)
            assert len(entries) == 30


class TestGetOptimalTargets:
    def test_returns_all_metric_keys(self):
        targets = get_optimal_targets()
        assert set(targets.keys()) == METRIC_KEYS

    def test_all_values_are_numeric(self):
        targets = get_optimal_targets()
        for key, value in targets.items():
            assert isinstance(value, (int, float)), f"{key} target is not numeric"

    def test_all_values_are_positive(self):
        targets = get_optimal_targets()
        for key, value in targets.items():
            assert value > 0, f"{key} target should be positive"

    def test_returns_copy_not_reference(self):
        """Mutating the returned dict must not affect the internal store."""
        targets = get_optimal_targets()
        targets["sleep"] = 999
        assert get_optimal_targets()["sleep"] == 8.0

    def test_specific_target_values(self):
        targets = get_optimal_targets()
        assert targets["sleep"] == 8.0
        assert targets["steps"] == 10000
        assert targets["resting_hr"] == 60
        assert targets["water"] == 2.5
        assert targets["workouts"] == 1
        assert targets["hrv"] == 60
