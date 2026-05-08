"""
api.py — FastAPI application for the weekly health tracker.

Endpoints:
  GET  /metrics/{user_id}  — return raw weekly metrics for a user
  POST /chat               — classify prompt, execute chains, return response blocks

Startup check: DEEPSEEK_API_KEY must be present in the environment or the app
raises EnvironmentError immediately rather than failing at the first request.
"""

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chain_executor import execute_chains
from classifier import classify
from data_store import get_user_metrics
from response_assembler import assemble

# ---------------------------------------------------------------------------
# Startup guard — fail fast if the API key is missing
# ---------------------------------------------------------------------------

if not os.environ.get("DEEPSEEK_API_KEY"):
    raise EnvironmentError(
        "DEEPSEEK_API_KEY environment variable is not set. "
        "Set it before starting the server."
    )

app = FastAPI(title="Weekly Health Tracker")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str
    prompt: str

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


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@app.post("/chat")
def chat(request: ChatRequest):
    """Classify a prompt, execute chains, and return labelled response blocks.

    Pipeline: classifier → chain_executor → response_assembler

    Returns:
        200 (valid):   {"valid": true,  "blocks": [{"label": str, "response": str}]}
        200 (invalid): {"valid": false, "reason": str}
        404:           {"error": "User not found"} for an unknown user_id.
        500:           {"error": str} for unexpected upstream failures.
    """
    # Validate user exists before calling the LLM
    try:
        get_user_metrics(request.user_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Classify — returns immediately with reason if invalid
    try:
        classification = classify(request.user_id, request.prompt)
    except (EnvironmentError, RuntimeError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if not classification["valid"]:
        return {"valid": False, "reason": classification["reason"]}

    # Execute chains concurrently for each sub-request
    try:
        chain_results = execute_chains(request.user_id, classification["sub_requests"])
    except (EnvironmentError, ValueError, RuntimeError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    # Assemble into labelled blocks (assembler result is for internal use;
    # the API returns the structured blocks list, not the flat string)
    blocks = [
        {"label": result["label"], "response": result["response"]}
        for result in chain_results
    ]

    return {"valid": True, "blocks": blocks}
