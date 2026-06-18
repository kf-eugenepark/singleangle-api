from typing import List, Dict, Optional


def collect_sources(topic: str, audience: str = "", provided_sources: Optional[List[Dict]] = None, depth: str = "standard") -> List[Dict]:
    """
    Source collection layer.

    For M365 Copilot, this replaces Claude Code's ability to run local scripts directly.
    Copilot calls the API. The API runs this Python logic.

    v0 behavior:
    - If caller provides source_texts, use those.
    - If no source_texts are provided, return an empty source list.

    Add real providers here:
    - Reddit search provider
    - X / Twitter search provider
    - Web search provider
    - Perplexity / Bing / custom search provider
    """
    if provided_sources:
        cleaned = []
        for i, source in enumerate(provided_sources):
            text = (source.get("text") or "").strip()
            if not text:
                continue
            cleaned.append({
                "id": f"provided-{i+1}",
                "title": source.get("title") or f"Provided source {i+1}",
                "url": source.get("url"),
                "text": text,
                "source_type": source.get("source_type") or "provided"
            })
        return cleaned

    return []
