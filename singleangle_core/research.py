from typing import List, Dict, Optional
import os
import requests


def collect_sources(
    topic: str,
    audience: str = "",
    provided_sources: Optional[List[Dict]] = None,
    depth: str = "standard"
) -> List[Dict]:
    """
    Source collection layer.

    v1 behavior:
    - Uses provided sources if available
    - Adds OpenAI synthesis as an additional "source"
    - Never crashes if provider fails
    """

    sources: List[Dict] = []

    # ✅ Step 1 — provided sources (unchanged)
    if provided_sources:
        for i, source in enumerate(provided_sources):
            text = (source.get("text") or "").strip()
            if not text:
                continue

            sources.append({
                "id": f"provided-{i+1}",
                "title": source.get("title") or f"Provided source {i+1}",
                "url": source.get("url"),
                "text": text,
                "source_type": source.get("source_type") or "provided"
            })

    # ✅ Step 2 — skip providers if light mode
    if depth == "light":
        return sources

    # ✅ Step 3 — OpenAI provider (safe)
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-5")

    if api_key:
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "input": f"""
Analyze real-world discussion patterns around this topic.

Topic: {topic}
Audience: {audience}

Return:
- key pain points
