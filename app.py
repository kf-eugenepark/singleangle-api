import os
import requests

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from singleangle_core.research import collect_sources
from singleangle_core.lenses import generate_candidate_angles
from singleangle_core.scoring import score_angles
from singleangle_core.brief import assemble_brief

app = FastAPI(
    title="SingleAngle API",
    description="Research a topic, generate candidate content angles, score them, and return one structured content brief.",
    version="0.1.1"
)


class SourceInput(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    text: str
    source_type: Optional[str] = Field(
        default="provided",
        description="web, reddit, x, provided, internal, etc."
    )


class SingleAngleRequest(BaseModel):
    topic: str = Field(..., description="The topic to research and turn into one sharp content angle.")
    audience: Optional[str] = Field(default="", description="Optional audience or ICP context.")
    source_texts: Optional[List[SourceInput]] = Field(
        default=None,
        description="Optional pre-collected sources. If omitted, providers can collect sources."
    )
    depth: Optional[str] = Field(default="standard", description="light, standard, or deep")


@app.get("/health")
def health():
    return {"status": "ok", "version": "debug-v2"}


def _safe_response_body(response):
    try:
        return response.json()
    except Exception:
        return response.text[:2000]


@app.get("/debug-env")
def debug_env():
    return {
        "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "xai_configured": bool(os.environ.get("XAI_API_KEY")),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "xai_model": os.environ.get("XAI_MODEL", "grok-4.3")
    }


@app.post("/debug-openai")
def debug_openai():
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        return {
            "provider": "openai",
            "status": "error",
            "error": "OPENAI_API_KEY is not configured in Railway variables."
        }

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": "Reply with exactly: ok"
            },
            timeout=15
        )

        return {
            "provider": "openai",
            "status": "ok" if response.ok else "error",
            "http_status": response.status_code,
            "model": model,
            "body": _safe_response_body(response)
        }

    except Exception as e:
        return {
            "provider": "openai",
            "status": "error",
            "error": str(e)
        }


@app.post("/debug-xai")
def debug_xai():
    api_key = os.environ.get("XAI_API_KEY")
    model = os.environ.get("XAI_MODEL", "grok-4.3")

    if not api_key:
        return {
            "provider": "xai",
            "status": "error",
            "error": "XAI_API_KEY is not configured in Railway variables."
        }

    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with exactly: ok"
                    }
                ],
                "temperature": 0
            },
            timeout=15
        )

        return {
            "provider": "xai",
            "status": "ok" if response.ok else "error",
            "http_status": response.status_code,
            "model": model,
            "body": _safe_response_body(response)
        }

    except Exception as e:
        return {
            "provider": "xai",
            "status": "error",
            "error": str(e)
        }


@app.post("/singleangle")
def singleangle(req: SingleAngleRequest) -> Dict[str, Any]:
    sources = collect_sources(
        topic=req.topic,
        audience=req.audience or "",
        provided_sources=[s.model_dump() for s in req.source_texts] if req.source_texts else None,
        depth=req.depth or "standard"
    )

    candidates = generate_candidate_angles(
        topic=req.topic,
        audience=req.audience or "",
        sources=sources
    )

    scored = score_angles(
        candidates=candidates,
        sources=sources,
        audience=req.audience or ""
    )

    brief = assemble_brief(
        topic=req.topic,
        audience=req.audience or "",
        sources=sources,
        scored_angles=scored
    )

    return {
        "debug": "singleangle_live_call",
        "brief": brief,
        "source_count": len(sources),
        "source_types": [s.get("source_type") for s in sources]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
