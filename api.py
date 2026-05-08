"""
api.py — FastAPI application for the weekly health tracker.

Endpoints:
  GET  /metrics/{user_id}  — return raw weekly metrics for a user
  POST /chat               — classify prompt, execute chains, return response blocks
                             (POST /chat implemented in a later issue)
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from data_store import get_user_metrics

app = FastAPI(title="Weekly Health Tracker")


# ---------------------------------------------------------------------------
# GET /metrics/{user_id}
# ---------------------------------------------------------------------------

@app.get("/metrics/{user_id}")
def metrics(user_id: str):
    """Return raw weekly health metrics for the given user.

    Returns:
        200: dict with all 6 metrics; unlogged metrics are JSON null.
        404: {"error": "User not found"} for an unknown user_id.
    """
    try:
        data = get_user_metrics(user_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "User not found"})
    return data
