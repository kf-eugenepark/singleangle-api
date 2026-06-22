from typing import List, Dict, Optional


def collect_sources(
    topic: str,
    audience: str = "",
    provided_sources: Optional[List[Dict]] = None,
    depth: str = "standard",
    provider_keys: Optional[Dict] = None,
) -> List[Dict]:
    """
    Stable source collection layer.

    This version does not call OpenAI, xAI, or Perplexity.
    It only uses source_texts passed into the request.
    """

    sources: List[Dict] = []

    if provided_sources:
        for i, source in enumerate(provided_sources):
            text = (source.get("text") or "").strip()
            if not text:
                continue

            sources.append({
                "id": f"provided-{i + 1}",
                "title": source.get("title") or f"Provided source {i + 1}",
                "url": source.get("url"),
                "text": text,
                "source_type": source.get("source_type") or "provided"
            })

    return sources
