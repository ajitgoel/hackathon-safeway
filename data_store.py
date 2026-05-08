"""
data_store.py — In-memory hardcoded user health metrics and optimal targets.

All data is hardcoded for the hackathon MVP. No database dependency.

Each user has 30 daily metric entries (one per day for the last month).
Any unlogged metric for a given day is represented as None.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Hardcoded user records
# Keys: user_id (str) → list of 30 daily metric dicts
# Each daily dict has: date (ISO string) + 6 metric keys:
#   sleep (hours), steps (count), resting_hr (bpm),
#   water (litres), workouts (0 or 1), hrv (ms)
# None represents a metric the user did not log that day.
# ---------------------------------------------------------------------------

_USERS: dict[str, list[dict[str, Optional[float]]]] = {
    # ------------------------------------------------------------------
    # User 1 — moderate performer, inconsistent HRV logging
    # ------------------------------------------------------------------
    "1": [
        {"date": "2026-04-09", "sleep": 7.0, "steps": 9200,  "resting_hr": 68, "water": 2.1, "workouts": 1, "hrv": 54},
        {"date": "2026-04-10", "sleep": 6.5, "steps": 8100,  "resting_hr": 71, "water": 1.9, "workouts": 0, "hrv": None},
        {"date": "2026-04-11", "sleep": 7.5, "steps": 10300, "resting_hr": 66, "water": 2.3, "workouts": 1, "hrv": 58},
        {"date": "2026-04-12", "sleep": 6.0, "steps": 7500,  "resting_hr": 74, "water": 1.7, "workouts": 0, "hrv": None},
        {"date": "2026-04-13", "sleep": 8.0, "steps": 11200, "resting_hr": 64, "water": 2.5, "workouts": 1, "hrv": 61},
        {"date": "2026-04-14", "sleep": 7.2, "steps": 9800,  "resting_hr": 67, "water": 2.2, "workouts": 0, "hrv": 55},
        {"date": "2026-04-15", "sleep": 6.8, "steps": 8600,  "resting_hr": 70, "water": 2.0, "workouts": 1, "hrv": None},
        {"date": "2026-04-16", "sleep": 7.1, "steps": 9400,  "resting_hr": 69, "water": 2.1, "workouts": 1, "hrv": 57},
        {"date": "2026-04-17", "sleep": 5.5, "steps": 6200,  "resting_hr": 78, "water": 1.5, "workouts": 0, "hrv": None},
        {"date": "2026-04-18", "sleep": 7.8, "steps": 10500, "resting_hr": 65, "water": 2.4, "workouts": 1, "hrv": 60},
        {"date": "2026-04-19", "sleep": 7.3, "steps": 9700,  "resting_hr": 67, "water": 2.2, "workouts": 0, "hrv": 56},
        {"date": "2026-04-20", "sleep": 6.9, "steps": 8900,  "resting_hr": 70, "water": 2.0, "workouts": 1, "hrv": None},
        {"date": "2026-04-21", "sleep": 8.1, "steps": 11000, "resting_hr": 63, "water": 2.6, "workouts": 1, "hrv": 63},
        {"date": "2026-04-22", "sleep": 7.0, "steps": 9100,  "resting_hr": 68, "water": 2.1, "workouts": 0, "hrv": 54},
        {"date": "2026-04-23", "sleep": 6.4, "steps": 7800,  "resting_hr": 73, "water": 1.8, "workouts": 0, "hrv": None},
        {"date": "2026-04-24", "sleep": 7.6, "steps": 10200, "resting_hr": 66, "water": 2.3, "workouts": 1, "hrv": 59},
        {"date": "2026-04-25", "sleep": 7.2, "steps": 9500,  "resting_hr": 68, "water": 2.2, "workouts": 1, "hrv": 57},
        {"date": "2026-04-26", "sleep": 6.7, "steps": 8300,  "resting_hr": 71, "water": 1.9, "workouts": 0, "hrv": None},
        {"date": "2026-04-27", "sleep": 7.9, "steps": 10800, "resting_hr": 64, "water": 2.5, "workouts": 1, "hrv": 62},
        {"date": "2026-04-28", "sleep": 7.4, "steps": 9900,  "resting_hr": 66, "water": 2.3, "workouts": 1, "hrv": 58},
        {"date": "2026-04-29", "sleep": 6.2, "steps": 7200,  "resting_hr": 75, "water": 1.6, "workouts": 0, "hrv": None},
        {"date": "2026-04-30", "sleep": 7.0, "steps": 9000,  "resting_hr": 69, "water": 2.1, "workouts": 0, "hrv": 55},
        {"date": "2026-05-01", "sleep": 7.5, "steps": 10100, "resting_hr": 66, "water": 2.3, "workouts": 1, "hrv": 59},
        {"date": "2026-05-02", "sleep": 6.8, "steps": 8700,  "resting_hr": 70, "water": 2.0, "workouts": 1, "hrv": None},
        {"date": "2026-05-03", "sleep": 8.2, "steps": 11300, "resting_hr": 63, "water": 2.7, "workouts": 1, "hrv": 64},
        {"date": "2026-05-04", "sleep": 7.1, "steps": 9300,  "resting_hr": 68, "water": 2.1, "workouts": 0, "hrv": 56},
        {"date": "2026-05-05", "sleep": 6.6, "steps": 8000,  "resting_hr": 72, "water": 1.8, "workouts": 0, "hrv": None},
        {"date": "2026-05-06", "sleep": 7.7, "steps": 10400, "resting_hr": 65, "water": 2.4, "workouts": 1, "hrv": 61},
        {"date": "2026-05-07", "sleep": 7.3, "steps": 9600,  "resting_hr": 67, "water": 2.2, "workouts": 1, "hrv": 57},
        {"date": "2026-05-08", "sleep": 6.5, "steps": 8200,  "resting_hr": 72, "water": 1.9, "workouts": 0, "hrv": None},
    ],

    # ------------------------------------------------------------------
    # User 2 — high performer, all metrics consistently logged
    # ------------------------------------------------------------------
    "2": [
        {"date": "2026-04-09", "sleep": 8.0, "steps": 12000, "resting_hr": 56, "water": 2.8, "workouts": 1, "hrv": 68},
        {"date": "2026-04-10", "sleep": 7.8, "steps": 11500, "resting_hr": 57, "water": 2.7, "workouts": 1, "hrv": 66},
        {"date": "2026-04-11", "sleep": 8.2, "steps": 12500, "resting_hr": 55, "water": 3.0, "workouts": 1, "hrv": 70},
        {"date": "2026-04-12", "sleep": 7.5, "steps": 10800, "resting_hr": 59, "water": 2.5, "workouts": 0, "hrv": 63},
        {"date": "2026-04-13", "sleep": 8.5, "steps": 13000, "resting_hr": 54, "water": 3.1, "workouts": 1, "hrv": 72},
        {"date": "2026-04-14", "sleep": 8.1, "steps": 12200, "resting_hr": 56, "water": 2.9, "workouts": 1, "hrv": 69},
        {"date": "2026-04-15", "sleep": 7.9, "steps": 11800, "resting_hr": 57, "water": 2.8, "workouts": 0, "hrv": 67},
        {"date": "2026-04-16", "sleep": 8.3, "steps": 12700, "resting_hr": 55, "water": 3.0, "workouts": 1, "hrv": 71},
        {"date": "2026-04-17", "sleep": 7.6, "steps": 11000, "resting_hr": 58, "water": 2.6, "workouts": 1, "hrv": 64},
        {"date": "2026-04-18", "sleep": 8.4, "steps": 13200, "resting_hr": 54, "water": 3.2, "workouts": 1, "hrv": 73},
        {"date": "2026-04-19", "sleep": 8.0, "steps": 12100, "resting_hr": 56, "water": 2.9, "workouts": 0, "hrv": 68},
        {"date": "2026-04-20", "sleep": 7.7, "steps": 11300, "resting_hr": 58, "water": 2.7, "workouts": 1, "hrv": 65},
        {"date": "2026-04-21", "sleep": 8.6, "steps": 13500, "resting_hr": 53, "water": 3.3, "workouts": 1, "hrv": 75},
        {"date": "2026-04-22", "sleep": 8.1, "steps": 12300, "resting_hr": 56, "water": 2.9, "workouts": 1, "hrv": 69},
        {"date": "2026-04-23", "sleep": 7.8, "steps": 11600, "resting_hr": 57, "water": 2.8, "workouts": 0, "hrv": 66},
        {"date": "2026-04-24", "sleep": 8.2, "steps": 12600, "resting_hr": 55, "water": 3.0, "workouts": 1, "hrv": 70},
        {"date": "2026-04-25", "sleep": 7.9, "steps": 11900, "resting_hr": 57, "water": 2.8, "workouts": 1, "hrv": 67},
        {"date": "2026-04-26", "sleep": 8.0, "steps": 12000, "resting_hr": 56, "water": 2.9, "workouts": 1, "hrv": 68},
        {"date": "2026-04-27", "sleep": 8.3, "steps": 12800, "resting_hr": 55, "water": 3.1, "workouts": 1, "hrv": 71},
        {"date": "2026-04-28", "sleep": 7.7, "steps": 11200, "resting_hr": 58, "water": 2.7, "workouts": 0, "hrv": 65},
        {"date": "2026-04-29", "sleep": 8.5, "steps": 13100, "resting_hr": 54, "water": 3.2, "workouts": 1, "hrv": 73},
        {"date": "2026-04-30", "sleep": 8.0, "steps": 12000, "resting_hr": 56, "water": 2.9, "workouts": 1, "hrv": 68},
        {"date": "2026-05-01", "sleep": 7.8, "steps": 11700, "resting_hr": 57, "water": 2.8, "workouts": 1, "hrv": 66},
        {"date": "2026-05-02", "sleep": 8.4, "steps": 13300, "resting_hr": 54, "water": 3.2, "workouts": 1, "hrv": 74},
        {"date": "2026-05-03", "sleep": 8.1, "steps": 12400, "resting_hr": 56, "water": 3.0, "workouts": 0, "hrv": 69},
        {"date": "2026-05-04", "sleep": 7.9, "steps": 11800, "resting_hr": 57, "water": 2.8, "workouts": 1, "hrv": 67},
        {"date": "2026-05-05", "sleep": 8.2, "steps": 12600, "resting_hr": 55, "water": 3.0, "workouts": 1, "hrv": 70},
        {"date": "2026-05-06", "sleep": 8.0, "steps": 12100, "resting_hr": 56, "water": 2.9, "workouts": 1, "hrv": 68},
        {"date": "2026-05-07", "sleep": 7.6, "steps": 11100, "resting_hr": 58, "water": 2.6, "workouts": 0, "hrv": 64},
        {"date": "2026-05-08", "sleep": 8.3, "steps": 12900, "resting_hr": 55, "water": 3.1, "workouts": 1, "hrv": 71},
    ],

    # ------------------------------------------------------------------
    # User 3 — struggling performer, frequent null metrics (sleep + HRV gaps)
    # ------------------------------------------------------------------
    "3": [
        {"date": "2026-04-09", "sleep": None, "steps": 4500,  "resting_hr": 82, "water": 1.2, "workouts": 0, "hrv": 38},
        {"date": "2026-04-10", "sleep": 5.5,  "steps": 5200,  "resting_hr": 80, "water": 1.3, "workouts": 0, "hrv": None},
        {"date": "2026-04-11", "sleep": None, "steps": 3800,  "resting_hr": 85, "water": 1.0, "workouts": 0, "hrv": 35},
        {"date": "2026-04-12", "sleep": 6.0,  "steps": 6100,  "resting_hr": 79, "water": 1.5, "workouts": 1, "hrv": None},
        {"date": "2026-04-13", "sleep": 5.0,  "steps": 4200,  "resting_hr": 83, "water": 1.1, "workouts": 0, "hrv": 36},
        {"date": "2026-04-14", "sleep": None, "steps": 3500,  "resting_hr": 86, "water": 0.9, "workouts": 0, "hrv": None},
        {"date": "2026-04-15", "sleep": 6.5,  "steps": 7000,  "resting_hr": 77, "water": 1.7, "workouts": 1, "hrv": 41},
        {"date": "2026-04-16", "sleep": 5.8,  "steps": 5500,  "resting_hr": 80, "water": 1.4, "workouts": 0, "hrv": None},
        {"date": "2026-04-17", "sleep": None, "steps": 4000,  "resting_hr": 84, "water": 1.1, "workouts": 0, "hrv": 37},
        {"date": "2026-04-18", "sleep": 5.2,  "steps": 4800,  "resting_hr": 82, "water": 1.2, "workouts": 0, "hrv": None},
        {"date": "2026-04-19", "sleep": 6.2,  "steps": 6500,  "resting_hr": 78, "water": 1.6, "workouts": 1, "hrv": 40},
        {"date": "2026-04-20", "sleep": None, "steps": 3200,  "resting_hr": 87, "water": 0.8, "workouts": 0, "hrv": None},
        {"date": "2026-04-21", "sleep": 5.5,  "steps": 5000,  "resting_hr": 81, "water": 1.3, "workouts": 0, "hrv": 38},
        {"date": "2026-04-22", "sleep": 6.0,  "steps": 6200,  "resting_hr": 79, "water": 1.5, "workouts": 1, "hrv": None},
        {"date": "2026-04-23", "sleep": None, "steps": 4100,  "resting_hr": 83, "water": 1.0, "workouts": 0, "hrv": 36},
        {"date": "2026-04-24", "sleep": 5.7,  "steps": 5300,  "resting_hr": 80, "water": 1.4, "workouts": 0, "hrv": None},
        {"date": "2026-04-25", "sleep": 6.3,  "steps": 6800,  "resting_hr": 77, "water": 1.7, "workouts": 1, "hrv": 42},
        {"date": "2026-04-26", "sleep": None, "steps": 3700,  "resting_hr": 85, "water": 1.0, "workouts": 0, "hrv": None},
        {"date": "2026-04-27", "sleep": 5.4,  "steps": 4900,  "resting_hr": 82, "water": 1.2, "workouts": 0, "hrv": 37},
        {"date": "2026-04-28", "sleep": 6.1,  "steps": 6300,  "resting_hr": 78, "water": 1.6, "workouts": 1, "hrv": None},
        {"date": "2026-04-29", "sleep": None, "steps": 3900,  "resting_hr": 84, "water": 1.1, "workouts": 0, "hrv": 35},
        {"date": "2026-04-30", "sleep": 5.6,  "steps": 5100,  "resting_hr": 81, "water": 1.3, "workouts": 0, "hrv": None},
        {"date": "2026-05-01", "sleep": 6.4,  "steps": 6900,  "resting_hr": 77, "water": 1.8, "workouts": 1, "hrv": 43},
        {"date": "2026-05-02", "sleep": None, "steps": 4300,  "resting_hr": 83, "water": 1.1, "workouts": 0, "hrv": None},
        {"date": "2026-05-03", "sleep": 5.3,  "steps": 4700,  "resting_hr": 82, "water": 1.2, "workouts": 0, "hrv": 38},
        {"date": "2026-05-04", "sleep": 6.0,  "steps": 6000,  "resting_hr": 79, "water": 1.5, "workouts": 1, "hrv": None},
        {"date": "2026-05-05", "sleep": None, "steps": 3600,  "resting_hr": 86, "water": 0.9, "workouts": 0, "hrv": 34},
        {"date": "2026-05-06", "sleep": 5.9,  "steps": 5600,  "resting_hr": 80, "water": 1.4, "workouts": 0, "hrv": None},
        {"date": "2026-05-07", "sleep": 6.5,  "steps": 7100,  "resting_hr": 76, "water": 1.8, "workouts": 1, "hrv": 44},
        {"date": "2026-05-08", "sleep": None, "steps": 4400,  "resting_hr": 83, "water": 1.1, "workouts": 0, "hrv": None},
    ],
}

# ---------------------------------------------------------------------------
# Expert-defined optimal targets — static daily constants, never computed
# ---------------------------------------------------------------------------

_OPTIMAL_TARGETS: dict[str, float] = {
    "sleep":      8.0,    # hours per night
    "steps":      10000,  # steps per day
    "resting_hr": 60,     # bpm (lower is better; this is the upper-bound target)
    "water":      2.5,    # litres per day
    "workouts":   1,      # sessions per day (≈5 per week)
    "hrv":        60,     # ms (higher is better; this is the lower-bound target)
}

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

EXPECTED_METRIC_KEYS = {"date", "sleep", "steps", "resting_hr", "water", "workouts", "hrv"}


def get_user_metrics(user_id: str) -> list[dict]:
    """Return the 30-day list of daily metric dicts for the given user.

    Each dict contains a ``date`` key (ISO string) and all 6 metric keys.
    Any unlogged metric for a given day is represented as ``None``.

    Args:
        user_id: String identifier for the user.

    Returns:
        List of 30 dicts, ordered oldest-first.

    Raises:
        KeyError: If user_id does not exist in the data store.
    """
    if user_id not in _USERS:
        raise KeyError(f"User '{user_id}' not found.")
    # Shallow-copy each day dict so callers cannot mutate internal state.
    return [dict(day) for day in _USERS[user_id]]


def get_optimal_targets() -> dict[str, float]:
    """Return the static dict of expert-defined optimal daily targets.

    Returns:
        Dict with keys: sleep, steps, resting_hr, water, workouts, hrv.
    """
    return dict(_OPTIMAL_TARGETS)
