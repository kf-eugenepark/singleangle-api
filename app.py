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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Repo layout:
#   /app.py
#   /brief_synthesis.py
#   /scripts/singleangle-research.py
#   /scripts/lib/
#   /static/index.html
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).parent.resolve()
SCRIPTS_DIR = REPO_ROOT / "scripts"
STATIC_DIR  = REPO_ROOT / "static"

sys.path.insert(0, str(SCRIPTS_DIR))


def _load_engine():
    engine_path = SCRIPTS_DIR / "singleangle-research.py"
    spec = importlib.util.spec_from_file_location("singleangle_research", str(engine_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = _load_engine()

from lib import env as sa_env
from lib import models as sa_models
from lib import render as sa_render
from lib import dates as sa_dates
from lib import schema as sa_schema

import brief_synthesis as sa_brief


app = FastAPI(
    title="SingleAngle API (async wrapper)",
    description="Async wrapper around the original singleangle research engine + brief synthesis.",
    version="0.6.0"
)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return {"status": "ok", "version": app.version, "ui": "missing static/index.html"}
    return FileResponse(str(index_path))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    topic: str = Field(..., description="Topic to research.")
    audience: Optional[str] = Field(default="", description="Optional audience or ICP context.")
    depth: Optional[str] = Field(default="default", description="quick | default | deep")
    days: Optional[int] = Field(default=30, description="Lookback window in days (1-30).")
    sources: Optional[str] = Field(default="auto", description="auto | reddit | x | both | web")
    x_source: Optional[str] = Field(default="xai", description="xai | bird")


class StartResponse(BaseModel):
    job_id: str
    status: str
    started_at: str


class BriefRequest(BaseModel):
    job_id: str = Field(..., description="Existing completed job_id.")
    audience: Optional[str] = Field(default=None, description="Override audience for synthesis.")
    model: Optional[str] = Field(default="gpt-5.5", description="OpenAI model id.")


JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def _new_job_record(req: StartRequest):
    return {
        "job_id": str(uuid.uuid4()),
        "status": "running",
        "phase": "initializing",
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


def _set_phase(job_id, phase):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["phase"] = phase


def _provider_event(job_id, name, **fields):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id]["providers"][name].update(fields)


def _ensure_list_of_dicts(items):
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(item)
        elif hasattr(item, "to_dict"):
            out.append(item.to_dict())
    return out


def _build_report(topic, from_date, to_date, effective_sources, selected_models, result_tuple):
    reddit_items_raw = []
    x_items_raw = []
    reddit_error = None
    x_error = None

    if isinstance(result_tuple, tuple):
        if len(result_tuple) >= 1 and isinstance(result_tuple[0], list):
            reddit_items_raw = result_tuple[0]
        if len(result_tuple) >= 2 and isinstance(result_tuple[1], list):
            x_items_raw = result_tuple[1]
        if len(result_tuple) >= 6 and isinstance(result_tuple[5], str):
            reddit_error = result_tuple[5]
        if len(result_tuple) >= 7 and isinstance(result_tuple[6], str):
            x_error = result_tuple[6]

    reddit_dicts = _ensure_list_of_dicts(reddit_items_raw)
    x_dicts      = _ensure_list_of_dicts(x_items_raw)

    payload = {
        "topic": topic,
        "range": {"from": from_date, "to": to_date},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": effective_sources,
        "openai_model_used": (selected_models or {}).get("openai"),
        "xai_model_used": (selected_models or {}).get("xai"),
        "reddit": reddit_dicts,
        "x": x_dicts,
        "web": [],
    }
    if reddit_error:
        payload["reddit_error"] = reddit_error
    if x_error:
        payload["x_error"] = x_error

    report = sa_schema.Report.from_dict(payload)
    return report, reddit_dicts, x_dicts, reddit_error, x_error


def _run_job(job_id):
    started = time.time()
    try:
        with JOBS_LOCK:
            job = JOBS[job_id]
            topic = job["topic"]
            depth = job["depth"]
            days  = job["days"]
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
            raise RuntimeError("No valid sources for this configuration: " + str(source_warning))

        _set_phase(job_id, "selecting_models")
        selected_models = sa_models.get_models(config)

        _set_phase(job_id, "computing_date_range")
        from_date, to_date = sa_dates.get_date_range(days=days)

        _set_phase(job_id, "running_research")

        class _Progress:
            def __init__(self, job_id):
                self.job_id = job_id

            def start_reddit(self, *a, **kw):
                _provider_event(self.job_id, "openai_reddit", status="running", started=time.time())

            def done_reddit(self, *a, **kw):
                with JOBS_LOCK:
                    started_at = JOBS[self.job_id]["providers"]["openai_reddit"].get("started")
                duration = (time.time() - started_at) if started_at else None
                _provider_event(self.job_id, "openai_reddit",
                                status="done",
                                duration=round(duration, 2) if duration else None,
                                item_count=kw.get("item_count"))

            def error_reddit(self, *a, **kw):
                _provider_event(self.job_id, "openai_reddit", status="error",
                                error=kw.get("error") or (a[0] if a else None))

            def start_x(self, *a, **kw):
                _provider_event(self.job_id, "xai_x", status="running", started=time.time())

            def done_x(self, *a, **kw):
                with JOBS_LOCK:
                    started_at = JOBS[self.job_id]["providers"]["xai_x"].get("started")
                duration = (time.time() - started_at) if started_at else None
                _provider_event(self.job_id, "xai_x",
                                status="done",
                                duration=round(duration, 2) if duration else None,
                                item_count=kw.get("item_count"))

            def error_x(self, *a, **kw):
                _provider_event(self.job_id, "xai_x", status="error",
                                error=kw.get("error") or (a[0] if a else None))

            def start_supplemental(self, *a, **kw):
                _set_phase(self.job_id, "running_supplemental")

            def done_supplemental(self, *a, **kw):
                _set_phase(self.job_id, "supplemental_complete")

            def __getattr__(self, name):
                def _noop(*a, **kw):
                    _set_phase(self.job_id, "engine:" + name)
                return _noop

        progress = _Progress(job_id)

        result = engine.run_research(
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

        report, reddit_dicts, x_dicts, reddit_error, x_error = _build_report(
            topic, from_date, to_date, effective_sources, selected_models, result
        )

        _provider_event(job_id, "openai_reddit",
                        status="error" if reddit_error else "done",
                        item_count=len(reddit_dicts),
                        error=reddit_error)
        _provider_event(job_id, "xai_x",
                        status="error" if x_error else "done",
                        item_count=len(x_dicts),
                        error=x_error)

        _set_phase(job_id, "rendering_output")
        missing_keys = sa_env.get_missing_keys(config)

        research_markdown = sa_render.render_compact(report, missing_keys=missing_keys)
        full_markdown     = sa_render.render_full_report(report)
        context_markdown  = sa_render.render_context_snippet(report)
        report_json       = report.to_dict()

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
                "full_markdown": full_markdown,
                "context_markdown": context_markdown,
                "report_json": report_json,
                "source_warning": source_warning,
                "brief_markdown": None,
                "brief_model": None,
                "brief_generated_at": None,
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
            "message": "Job is still running. Poll /singleangle/status until it returns done."
        }

    if job["status"] == "error":
        return {
            "job_id": job["job_id"],
            "status": "error",
            "error": job["error"]
        }

    r = job["result"]
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
        "from_date": r["from_date"],
        "to_date": r["to_date"],
        "research_markdown": r["research_markdown"],
        "full_markdown": r.get("full_markdown"),
        "context_markdown": r.get("context_markdown"),
        "report_json": r["report_json"],
        "source_warning": r.get("source_warning"),
        "brief_markdown": r.get("brief_markdown"),
        "brief_model": r.get("brief_model"),
        "brief_generated_at": r.get("brief_generated_at"),
    }


@app.post("/singleangle/brief")
def brief(req: BriefRequest):
    with JOBS_LOCK:
        job = JOBS.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Job is not done yet. Wait for status:done.")

    r = job["result"]
    if r.get("brief_markdown"):
        return {
            "job_id": req.job_id,
            "status": "done",
            "cached": True,
            "brief_markdown": r["brief_markdown"],
            "brief_model": r.get("brief_model"),
            "brief_generated_at": r.get("brief_generated_at"),
        }

    audience = req.audience if (req.audience is not None) else job["audience"]
    model = req.model or "gpt-5.5"

    try:
        brief_md = sa_brief.assemble_brief(
            research_markdown=r["research_markdown"],
            topic=job["topic"],
            audience=audience or "",
            from_date=r["from_date"],
            to_date=r["to_date"],
            model=model,
        )
    except Exception as e:
        return {
            "job_id": req.job_id,
            "status": "error",
            "error": {"message": str(e)},
        }

    generated_at = datetime.now(timezone.utc).isoformat()
    with JOBS_LOCK:
        if req.job_id in JOBS and JOBS[req.job_id].get("result"):
            JOBS[req.job_id]["result"]["brief_markdown"] = brief_md
            JOBS[req.job_id]["result"]["brief_model"] = model
            JOBS[req.job_id]["result"]["brief_generated_at"] = generated_at

    return {
        "job_id": req.job_id,
        "status": "done",
        "cached": False,
        "brief_markdown": brief_md,
        "brief_model": model,
        "brief_generated_at": generated_at,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
