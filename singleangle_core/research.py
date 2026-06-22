from typing import List, Dict, Optional


def collect_sources(
    topic: str,
    audience: str = "",
    provided_sources: Optional[List[Dict]] = None,
    depth: str = "standard",
    provider_keys: Optional[Dict] = None,
) -> List[Dict]:

    sources: List[Dict] = []

    # 1. Include provided sources
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

    # 2. Skip external providers in light mode
    if depth == "light":
        return sources

    provider_keys = provider_keys or {}

    # 3. OpenAI (safe import)
    try:
        from singleangle_core.providers import openai_reddit_research

        sources.extend(openai_reddit_research(
            topic=topic,
            audience=audience,
            api_key=provider_keys.get("openai_api_key"),
            model=provider_keys.get("openai_model", "gpt-4o"),
            web_search_tool=provider_keys.get("openai_web_search_tool", "web_search_preview"),
        ))

    except Exception as e:
        sources.append({
            "id": "openai-error",
            "title": "OpenAI provider failed",
            "url": None,
            "source_type": "provider_error",
            "text": str(e)
        })

    # 4. xAI (safe import)
    try:
        from singleangle_core.providers import xai_x_research

        sources.extend(xai_x_research(
            topic=topic,
            audience=audience,
            api_key=provider_keys.get("xai_api_key"),
            model=provider_keys.get("xai_model", "grok-4.3"),
        ))

    except Exception as e:
        sources.append({
            "id": "xai-error",
            "title": "xAI provider failed",
            "url": None,
            "source_type": "provider_error",
            "text": str(e)
        })

    return sources
