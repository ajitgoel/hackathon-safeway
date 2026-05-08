"""
Unit tests for data_store.py.

Tests cover:
- Known user returns correct metrics
- Unknown user raises KeyError
- User with a null metric returns None for that metric
- get_optimal_targets returns a complete dict for all 6 metrics
"""

import pytest
from data_store import get_user_metrics, get_optimal_targets

EXPECTED_METRICS = {"sleep", "steps", "resting_hr", "water", "workouts", "hrv"}


class TestGetUserMetrics:
    def test_known_user_returns_all_metric_keys(self):
        metrics = get_user_metrics("1")
        assert set(metrics.keys()) == EXPECTED_METRICS

    def test_known_user_returns_correct_values(self):
        metrics = get_user_metrics("1")
        assert metrics["sleep"] == 6.5
        assert metrics["steps"] == 8200
        assert metrics["resting_hr"] == 72
        assert metrics["water"] == 1.8
        assert metrics["workouts"] == 3

    def test_known_user_with_null_hrv(self):
        """User 1 has HRV unlogged — should be None, not missing."""
        metrics = get_user_metrics("1")
        assert "hrv" in metrics
        assert metrics["hrv"] is None

    def test_known_user_with_null_sleep(self):
        """User 3 has sleep unlogged — should be None."""
        metrics = get_user_metrics("3")
        assert "sleep" in metrics
        assert metrics["sleep"] is None

    def test_known_user_all_metrics_present(self):
        """User 2 has all metrics logged — none should be None."""
        metrics = get_user_metrics("2")
        assert all(v is not None for v in metrics.values())

    def test_unknown_user_raises_key_error(self):
        with pytest.raises(KeyError):
            get_user_metrics("999")

    def test_unknown_user_string_id_raises_key_error(self):
        with pytest.raises(KeyError):
            get_user_metrics("unknown")

    def test_returns_copy_not_reference(self):
        """Mutating the returned dict must not affect the internal store."""
        metrics = get_user_metrics("1")
        metrics["sleep"] = 999
        assert get_user_metrics("1")["sleep"] == 6.5


class TestGetOptimalTargets:
    def test_returns_all_metric_keys(self):
        targets = get_optimal_targets()
        assert set(targets.keys()) == EXPECTED_METRICS

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
        assert targets["workouts"] == 5
        assert targets["hrv"] == 60
