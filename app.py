import os
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
    version="0.2.0"
)

class SourceInput(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    text: str
    source_type: Optional[str] = Field(default="provided", description="web, reddit, x, provided, internal, etc.")

class SingleAngleRequest(BaseModel):
    topic: str = Field(..., description="The topic to research and turn into one sharp content angle.")
    audience: Optional[str] = Field(default="", description="Optional audience or ICP context.")
    source_texts: Optional[List[SourceInput]] = Field(default=None, description="Optional pre-collected sources. If omitted, providers can collect sources.")
    depth: Optional[str] = Field(default="standard", description="light, standard, or deep")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}

@app.post("/singleangle")
def singleangle(req: SingleAngleRequest) -> Dict[str, Any]:
    provider_keys = {
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
        "xai_api_key": os.environ.get("XAI_API_KEY"),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-5"),
        "xai_model": os.environ.get("XAI_MODEL", "grok-4.3"),
        "openai_web_search_tool": os.environ.get("OPENAI_WEB_SEARCH_TOOL", "web_search_preview"),
    }

    sources = collect_sources(
        topic=req.topic,
        audience=req.audience or "",
        provided_sources=[s.model_dump() for s in req.source_texts] if req.source_texts else None,
        depth=req.depth or "standard",
        provider_keys=provider_keys,
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

    return brief
