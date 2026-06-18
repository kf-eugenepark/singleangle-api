from typing import List, Dict, Optional
from singleangle_core.providers import openai_reddit_research, xai_x_research


def collect_sources(
    topic: str,
    audience: str = "",
    provided_sources: Optional[List[Dict]] = None,
    depth: str = "standard",
    provider_keys: Optional[Dict] = None,
) -> List[Dict]:
    """
    Source collection layer.

    v0.2 behavior:
    - Includes user-provided source_texts if available.
    - Adds OpenAI-powered Reddit/forum research if OPENAI_API_KEY is configured.
    - Adds xAI/Grok-powered X discourse synthesis if XAI_API_KEY is configured.
    """
    sources: List[Dict] = []

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

    provider_keys = provider_keys or {}

    # Keep provider calls enabled for standard/deep. In light mode, only use user-provided sources.
    if depth != "light":
        sources.extend(openai_reddit_research(
            topic=topic,
            audience=audience,
            api_key=provider_keys.get("openai_api_key"),
            model=provider_keys.get("openai_model", "gpt-5"),
            web_search_tool=provider_keys.get("openai_web_search_tool", "web_search_preview"),
        ))

        sources.extend(xai_x_research(
            topic=topic,
            audience=audience,
            api_key=provider_keys.get("xai_api_key"),
            model=provider_keys.get("xai_model", "grok-4.3"),
        ))

    return sources
