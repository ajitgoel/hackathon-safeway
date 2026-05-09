"""
api.py — FastAPI application for the weekly health tracker.

Endpoints:
  GET  /metrics/{user_id}  — return raw weekly metrics for a user
  POST /chat               — classify prompt, execute chains, return response blocks
  POST /chat/stream        — same pipeline but streams the assembled response as
                             server-sent events (SSE) for lower perceived latency

Performance design:
  - /chat and /chat/stream are async; the event loop is never blocked.
  - User validation (in-memory) runs before classify() to avoid wasting an LLM
    call for an unknown user_id.
  - execute_chains() runs RunnableParallel inside asyncio.to_thread so LangChain's
    synchronous invoke does not stall the event loop.
  - The ChatOpenAI instance is a module-level singleton in chain_executor — no
    per-request setup overhead.

Startup check: GROQ_API_KEY must be present in the environment or the app
raises EnvironmentError immediately rather than failing at the first request.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from chain_executor import execute_chains
from classifier import classify
from data_store import get_user_metrics
from response_assembler import assemble

# ---------------------------------------------------------------------------
# Startup guard — fail fast if the API key is missing.
# Using lifespan so uvicorn binds the port before the check runs;
# this prevents Fly.io from reporting "app not listening on 0.0.0.0:8080".
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("GROQ_API_KEY"):
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Set it before starting the server."
        )
    yield


app = FastAPI(title="Weekly Health Tracker", lifespan=lifespan)


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
async def chat(request: ChatRequest):
    """Classify a prompt, execute chains, and return labelled response blocks.

    Pipeline: classifier → chain_executor → response_assembler

    User validation runs first (in-memory, instant) so we never waste an LLM
    call on an unknown user_id.

    Returns:
        200 (valid):   {"valid": true,  "blocks": [{"label": str, "response": str}]}
        200 (invalid): {"valid": false, "reason": str}
        404:           {"error": "User not found"} for an unknown user_id.
        500:           {"error": str} for unexpected upstream failures.
    """
    # Validate user exists before calling the LLM.
    try:
        get_user_metrics(request.user_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Classify — returns immediately with reason if invalid.
    try:
        classification = await classify(request.user_id, request.prompt)
    except (EnvironmentError, RuntimeError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if not classification["valid"]:
        return {"valid": False, "reason": classification["reason"]}

    # Execute chains concurrently for each sub-request.
    try:
        chain_results = await execute_chains(request.user_id, classification["sub_requests"])
    except (EnvironmentError, ValueError, RuntimeError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    blocks = [
        {"label": result["label"], "response": result["response"]}
        for result in chain_results
    ]

    return {"valid": True, "blocks": blocks}


# ---------------------------------------------------------------------------
# POST /chat/stream
# ---------------------------------------------------------------------------

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Same pipeline as POST /chat but streams the response as SSE.

    The assembled response is emitted as a server-sent event as soon as all
    chains complete, so the client can start rendering immediately.

    SSE format (each line):
        data: <content>\\n\\n

    A final sentinel event signals completion:
        data: [DONE]\\n\\n

    Returns:
        200: text/event-stream
        404: {"error": "User not found"}
        500: {"error": str}
    """
    # Validate user exists before calling the LLM.
    try:
        get_user_metrics(request.user_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Classify the prompt.
    try:
        classification = await classify(request.user_id, request.prompt)
    except (EnvironmentError, RuntimeError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if not classification["valid"]:
        # Return a single SSE event carrying the rejection reason.
        async def _invalid_stream():
            yield f"data: INVALID: {classification['reason']}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_invalid_stream(), media_type="text/event-stream")

    async def _stream_results():
        try:
            chain_results = await execute_chains(
                request.user_id, classification["sub_requests"]
            )
        except (EnvironmentError, ValueError, RuntimeError) as exc:
            yield f"data: ERROR: {exc}\n\n"
            yield "data: [DONE]\n\n"
            return

        assembled = assemble(chain_results)
        yield f"data: {assembled}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_stream_results(), media_type="text/event-stream")
