import os
import sys
import time
import uuid
import traceback
import threading
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Layout assumption (matches upstream singleangle):
#   /app.py
#   /scripts/singleangle-research.py
#   /scripts/lib/
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).parent.resolve()
SCRIPTS_DIR = REPO_ROOT / "scripts"

# IMPORTANT: add scripts/ to sys.path so `from lib import ...` resolves
# to scripts/lib/, exactly like the original CLI does.
sys.path.insert(0, str(SCRIPTS_DIR))

# Load singleangle-research.py as a module (its filename has a hyphen).
def _load_engine():
    engine_path = SCRIPTS_DIR / "singleangle-research.py"
    spec = importlib.util.spec_from_file_location("singleangle_research", str(engine_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

engine = _load_engine()

# Now lib helpers work the same way they do inside the original script
from lib import env as sa_env
from lib import models as sa_models
from lib import render as sa_render
from lib import dates as sa_dates


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SingleAngle API (async wrapper)",
    description="Async wrapper around the original singleangle research engine.",
    version="0.3.0"
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    topic: str = Field(..., description="Topic to research.")
    audience: Optional[str] = Field(default="", description="Optional audience or ICP context. Used by Copilot at brief synthesis time.")
    depth: Optional[str] = Field(default="default", description="quick | default | deep")
    days: Optional[int] = Field(default=30, description="Lookback window in days (1-30).")
    sources: Optional[str] = Field(default="auto", description="auto | reddit | x | both | web")
    x_source: Optional[str] = Field(default="xai", description="xai | bird")


class StartResponse(BaseModel):
    job_id: str
    status: str
    started_at: str


# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def _new_job_record(req: StartRequest) -> Dict[str, Any]:
    return {
        "job_id": str(uuid.uuid4()),
        "status": "running",       # running | done | error
        "phase": "initializing",   # human-readable phase
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "elapsed_seconds": 0.0,
        "topic": req.topic,
        "audience": req.audience or "",
        "depth": req.depth or "default",
        "days": req.days or 30,
        "sources": req.sources or "auto",
        "x_source": req.x_source or "xai",
        "providers": {
            "openai_reddit": {"status": "pending", "duration": None, "item_count": None, "error": None},
            "xai_x":         {"status": "pending", "duration": None, "item_count": None, "error": None},
            "websearch":     {"status": "pending", "duration": None, "item_count": None, "error": None},
        },
        "result": None,
        "error": None,
    }


def _set_phase(job_id: str, phase: str):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["phase"] = phase


def _provider_event(job_id: str, name: str, **fields):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["providers"][name].update(fields)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
def _run_job(job_id: str):
    started = time.time()
    try:
        with JOBS_LOCK:
            job = JOBS[job_id]
            topic = job["topic"]
            depth = job["depth"]
            days = job["days"]
            sources_requested = job["sources"]
            x_source = job["x_source"]

        _set_phase(job_id, "loading_config")

        config = sa_env.get_config()
        available = sa_env.get_available_sources(config)
        effective_sources, source_warning = sa_env.validate_sources(
            requested=sources_requested,
            available=available,
            include_web=False,
        )

        if effective_sources == "none":
            raise RuntimeError(f"No valid sources for this configuration: {source_warning}")

        _set_phase(job_id, "selecting_models")
        selected_models = sa_models.get_models(config)

        _set_phase(job_id, "computing_date_range")
        from_date, to_date = sa_dates.compute_range(days=days)

        _set_phase(job_id, "running_research")

        # Wrap provider timing using the progress hook the engine supports
        def progress(event: str, **kwargs):
            # Engine emits events like phase changes and provider lifecycle.
            # We map known events to the providers dict; unknown events just update phase.
            ev = event.lower()

            if "reddit" in ev and "start" in ev:
                _provider_event(job_id, "openai_reddit", status="running", started=time.time())
            elif "reddit" in ev and ("done" in ev or "complete" in ev):
                with JOBS_LOCK:
                    started_at = JOBS[job_id]["providers"]["openai_reddit"].get("started")
                duration = (time.time() - started_at) if started_at else None
                _provider_event(
                    job_id, "openai_reddit",
                    status="done",
                    duration=round(duration, 2) if duration else None,
                    item_count=kwargs.get("item_count"),
                )
            elif "reddit" in ev and "error" in ev:
                _provider_event(job_id, "openai_reddit", status="error", error=kwargs.get("error"))

            elif ev.startswith("x_") or " x " in ev or ev.startswith("x:"):
                if "start" in ev:
                    _provider_event(job_id, "xai_x", status="running", started=time.time())
                elif "done" in ev or "complete" in ev:
                    with JOBS_LOCK:
                        started_at = JOBS[job_id]["providers"]["xai_x"].get("started")
                    duration = (time.time() - started_at) if started_at else None
                    _provider_event(
                        job_id, "xai_x",
                        status="done",
                        duration=round(duration, 2) if duration else None,
                        item_count=kwargs.get("item_count"),
                    )
                elif "error" in ev:
                    _provider_event(job_id, "xai_x", status="error", error=kwargs.get("error"))

            elif "phase" in ev or "supplemental" in ev:
                _set_phase(job_id, event)

        report = engine.run_research(
            topic=topic,
            sources=effective_sources,
            config=config,
            selected_models=selected_models,
            from_date=from_date,
            to_date=to_date,
            depth=depth,
            mock=False,
            progress=progress,
            x_source=x_source,
        )

        _set_phase(job_id, "rendering_output")

        # Render compact markdown using the original render module.
        missing_keys = sa_env.get_missing_keys(config)
        research_markdown = sa_render.render_compact(report, missing_keys=missing_keys)

        # Also keep the structured report for clients that want JSON.
        report_json = report.to_dict() if hasattr(report, "to_dict") else None

        total = time.time() - started

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            JOBS[job_id]["elapsed_seconds"] = round(total, 2)
            JOBS[job_id]["phase"] = "complete"
            JOBS[job_id]["result"] = {
                "topic": topic,
                "audience": JOBS[job_id]["audience"],
                "from_date": from_date,
                "to_date": to_date,
                "research_markdown": research_markdown,
                "report_json": report_json,
                "source_warning": source_warning,
            }

    except Exception as e:
        tb = traceback.format_exc()
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                JOBS[job_id]["elapsed_seconds"] = round(time.time() - started, 2)
                JOBS[job_id]["phase"] = "error"
                JOBS[job_id]["error"] = {
                    "message": str(e),
                    "traceback": tb[-4000:],
                }


# ---------------------------------------------------------------------------
# Health + debug
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/debug-env")
def debug_env():
    config = sa_env.get_config()
    return {
        "openai_configured": bool(config.get("OPENAI_API_KEY")),
        "xai_configured": bool(config.get("XAI_API_KEY")),
        "openai_model_policy": config.get("OPENAI_MODEL_POLICY"),
        "xai_model_policy": config.get("XAI_MODEL_POLICY"),
        "available_sources": sa_env.get_available_sources(config),
    }


# ---------------------------------------------------------------------------
# Async endpoints
# ---------------------------------------------------------------------------
@app.post("/singleangle/start", response_model=StartResponse)
def start(req: StartRequest):
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")

    job = _new_job_record(req)
    with JOBS_LOCK:
        JOBS[job["job_id"]] = job

    t = threading.Thread(target=_run_job, args=(job["job_id"],), daemon=True)
    t.start()

    return StartResponse(
        job_id=job["job_id"],
        status="running",
        started_at=job["started_at"],
    )


@app.get("/singleangle/status")
def status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")

    elapsed = job.get("elapsed_seconds") or 0.0
    if job["status"] == "running":
        # live elapsed
        try:
            started_dt = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - started_dt).total_seconds()
        except Exception:
            pass

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "phase": job["phase"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "elapsed_seconds": round(elapsed, 2),
        "providers": job["providers"],
        "topic": job["topic"],
        "audience": job["audience"],
        "depth": job["depth"],
        "days": job["days"],
        "sources": job["sources"],
        "x_source": job["x_source"],
        "error": job.get("error"),
    }


@app.get("/singleangle/result")
def result(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")

    if job["status"] == "running":
        return {
            "job_id": job["job_id"],
            "status": "running",
            "message": "Job is still running. Poll /singleangle/status until it returns done.",
        }

    if job["status"] == "error":
        return {
            "job_id": job["job_id"],
            "status": "error",
            "error": job["error"],
        }

    return {
        "job_id": job["job_id"],
        "status": "done",
        "topic": job["topic"],
        "audience": job["audience"],
        "depth": job["depth"],
        "days": job["days"],
        "sources": job["sources"],
        "x_source": job["x_source"],
        "providers_timing": job["providers"],
        "total_duration_seconds": job["elapsed_seconds"],
        "from_date": job["result"]["from_date"],
        "to_date": job["result"]["to_date"],
        "research_markdown": job["result"]["research_markdown"],
        "report_json": job["result"]["report_json"],
        "source_warning": job["result"].get("source_warning"),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
