import os
import json
from queue import Queue
from threading import Thread
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models import CheckpointDecision, ResearchRequest, RunControlRequest
from .llm import resolve_provider
from .store import EvidenceStore
from .workflow import ResearchState, start_run


store = EvidenceStore()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if store.verify():
        store.initialize()
    yield
    store.close()


app = FastAPI(title="ForesightForge API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    connected = store.verify()
    provider, _key, config = resolve_provider(None, None)
    # Report the model that will actually be used, not just the provider
    # default. The provider registry falls back to a built-in default when
    # MODEL_NAME is unset, which may not be an installed model.
    effective_model = os.getenv("MODEL_NAME") or (config.get("default_model", "") if config else "")
    return {
        "status": "ok" if connected else "degraded",
        "graph": "connected" if connected else "unavailable",
        # The client uses this to preselect the provider. Without it the UI
        # would default to a hosted provider that may have no key, overriding
        # whatever the server was actually configured with.
        "model": {
            "provider": provider or "",
            "base_url": os.getenv("MODEL_BASE_URL") or (config.get("base_url", "") if config else ""),
            "default_model": effective_model,
        },
    }


@app.get("/api/runs")
def list_runs() -> list[dict[str, object]]:
    if not store.verify():
        return []
    return store.list_runs()


RND_STATE_FIELDS = (
    "plan",
    "subagent_executions",
    "citation_verifications",
    "evaluation",
    "forecast",
    "disagreements",
    "projections",
    "brainstormed_ideas",
    "overcome_strategies",
    "active_speaker",
    "core_architecture",
    "attempt_history",
    "intake",
    "clarifying_questions",
    "scope",
    "pain_points",
    "transcript",
    "panel_round",
    "convergence",
    "problem_candidates",
    "selected_problem_ids",
    "evidence",
    "gaps",
    "ideas",
    "critiques",
    "lineage",
    "validation_results",
    "ranked_ideas",
    "checkpoints",
    "spend",
    "limits",
    "mode",
)


def _run_record(request: ResearchRequest, result: ResearchState) -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, object] = {
        "id": result.get("run_id") or "unknown",
        "domain": request.domain,
        "question": request.question,
        "mode": result.get("mode") or "problem",
        "status": result.get("status") or "failed",
        "round": result.get("round") or 1,
        "attempt": result.get("attempt") or 1,
        "max_attempts": result.get("max_attempts") or 1,
        "current_stage": result.get("current_stage") or "verify",
        "spend": result.get("spend") or {"usd": 0.0, "tokens": 0, "calls": 0},
        "limits": result.get("limits") or {},
        "created_at": now,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "claims": result.get("claims", []),
        "sources": result.get("sources", []),
        "audit": result.get("audit", []),
    }
    for field in RND_STATE_FIELDS:
        value = result.get(field)
        if value:
            record[field] = value
    return record


def _start_kwargs(request: ResearchRequest) -> dict[str, object]:
    """Translate a request into workflow start arguments."""
    return {
        "model_provider": request.model_provider,
        "model_name": request.model_name,
        "api_key": request.api_key,
        "mode": request.mode,
        "depth": request.depth,
        "max_usd": request.max_usd,
        "max_rounds": request.max_rounds,
        "max_queries": request.max_queries,
        "max_sources": request.max_sources,
    }


@app.post("/api/runs")
def create_run(request: ResearchRequest) -> dict[str, object]:
    if not store.verify():
        raise HTTPException(status_code=503, detail="Evidence graph is unavailable")
    result = start_run(request.domain, request.question, **_start_kwargs(request))
    record = _run_record(request, result)
    store.save_run(record)
    return record


@app.post("/api/runs/stream")
def create_run_stream(request: ResearchRequest) -> StreamingResponse:
    if not store.verify():
        raise HTTPException(status_code=503, detail="Evidence graph is unavailable")

    def stream_events():
        events: Queue[dict[str, object] | None] = Queue()

        def publish(event: dict[str, object]) -> None:
            events.put(event)

        def execute_run() -> None:
            try:
                publish(
                    {
                        "type": "run_started",
                        "domain": request.domain,
                        "question": request.question,
                        "mode": request.mode,
                        "limits": {
                            "depth": request.depth,
                            "max_usd": request.max_usd,
                        },
                    }
                )
                result = start_run(
                    request.domain,
                    request.question,
                    progress_callback=publish,
                    **_start_kwargs(request),
                )
                record = _run_record(request, result)
                publish({"type": "run_persisting", "run_id": record["id"], "source_count": len(result.get("sources", []))})
                store.save_run(record)
                publish({"type": "run_saved", "run_id": record["id"]})
                publish({"type": "run_completed", "run": record})
            except Exception as error:
                publish({"type": "run_failed", "detail": f"{type(error).__name__}: {error}"})
            finally:
                events.put(None)

        worker = Thread(target=execute_run, daemon=True)
        worker.start()
        while True:
            event = events.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/runs/{run_id}/checkpoint")
def resolve_checkpoint(run_id: str, decision: CheckpointDecision) -> dict[str, object]:
    """Record a human decision on a pending checkpoint (FR-UX-2).

    The decision is stored on the run so the transcript and the report show
    what the human chose, edited or rejected.
    """
    if not store.verify():
        raise HTTPException(status_code=503, detail="Evidence graph is unavailable")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    checkpoints = list(run.get("checkpoints") or [])
    entry: dict[str, object] = {
        "id": decision.checkpoint_id or f"cp-{len(checkpoints) + 1}",
        "kind": "problem_selection",
        "action": decision.action,
        "selected_ids": decision.selected_ids,
        "edits": decision.edits,
        "note": decision.note,
        "redirect": decision.redirect,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "resolved": True,
    }
    checkpoints.append(entry)
    run["checkpoints"] = checkpoints
    run["status"] = "completed" if decision.action in {"approve", "select", "auto_select"} else "completed"
    run["selected_problem_ids"] = decision.selected_ids or run.get("selected_problem_ids", [])
    run["updated_at"] = datetime.now(timezone.utc).isoformat()
    store.save_run(run)
    return {"run_id": run_id, "checkpoint": entry}


@app.post("/api/runs/{run_id}/control")
def control_run(run_id: str, control: RunControlRequest) -> dict[str, object]:
    """Pause, resume or cancel a run (FR-UX-3).

    The run record carries the request so the UI reflects the requested state
    immediately; a live worker checks the flag at its next stage boundary.
    """
    if not store.verify():
        raise HTTPException(status_code=503, detail="Evidence graph is unavailable")
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    status = {"pause": "paused", "resume": "running", "cancel": "cancelled"}[control.action]
    run["status"] = status
    run["updated_at"] = datetime.now(timezone.utc).isoformat()
    store.save_run(run)
    return {"run_id": run_id, "status": status, "action": control.action}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    if not store.verify():
        raise HTTPException(status_code=503, detail="Evidence graph is unavailable")
    record = store.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record