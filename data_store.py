"""
data_store.py — In-memory hardcoded user health metrics and optimal targets.

All data is hardcoded for the hackathon MVP. No database dependency.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Hardcoded user records
# Keys: user_id (str) → metrics dict
# Metrics: sleep (hours), steps (count), resting_hr (bpm),
#          water (litres), workouts (count), hrv (ms)
# None represents a metric the user did not log that week.
# ---------------------------------------------------------------------------

_USERS: dict[str, dict[str, Optional[float]]] = {
    "1": {
        "sleep": 6.5,
        "steps": 8200,
        "resting_hr": 72,
        "water": 1.8,
        "workouts": 3,
        "hrv": None,          # user 1 did not log HRV
    },
    "2": {
        "sleep": 7.8,
        "steps": 11500,
        "resting_hr": 58,
        "water": 2.5,
        "workouts": 5,
        "hrv": 62,
    },
    "3": {
        "sleep": None,        # user 3 did not log sleep
        "steps": 4300,
        "resting_hr": 81,
        "water": 1.2,
        "workouts": 1,
        "hrv": 38,
    },
}

# ---------------------------------------------------------------------------
# Expert-defined optimal targets — static constants, never computed at runtime
# ---------------------------------------------------------------------------

_OPTIMAL_TARGETS: dict[str, float] = {
    "sleep": 8.0,        # hours per night
    "steps": 10000,      # steps per day
    "resting_hr": 60,    # bpm (lower is generally better; target is upper bound)
    "water": 2.5,        # litres per day
    "workouts": 5,       # sessions per week
    "hrv": 60,           # ms (higher is generally better; target is lower bound)
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_user_metrics(user_id: str) -> dict[str, Optional[float]]:
    """Return the weekly health metrics dict for the given user_id.

    Args:
        user_id: String identifier for the user.

    Returns:
        Dict with keys: sleep, steps, resting_hr, water, workouts, hrv.
        Any unlogged metric is represented as None.

    Raises:
        KeyError: If user_id does not exist in the data store.
    """
    if user_id not in _USERS:
        raise KeyError(f"User '{user_id}' not found.")
    return dict(_USERS[user_id])  # return a shallow copy to prevent mutation


def get_optimal_targets() -> dict[str, float]:
    """Return the static dict of expert-defined optimal targets for all metrics.

    Returns:
        Dict with keys: sleep, steps, resting_hr, water, workouts, hrv.
    """
    return dict(_OPTIMAL_TARGETS)  # return a shallow copy to prevent mutation
