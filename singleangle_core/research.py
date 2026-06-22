from typing import Dict, List, Optional
import os
import requests


def collect_sources(
    topic: str,
    audience: str = "",
    provided_sources: Optional[List[Dict]] = None,
    depth: str = "standard"
) -> List[Dict]:
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

    if depth == "light":
        return sources

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-5")

    if not api_key:
        sources.append({
            "id": "openai-missing-key",
            "title": "OpenAI skipped",
            "url": None,
            "text": "OPENAI_API_KEY is not configured in Railway variables.",
            "source_type": "provider_status"
        })
        return sources

    prompt = (
        "Analyze real-world discussion patterns around this topic.\n\n"
        f"Topic: {topic}\n"
        f"Audience: {audience}\n\n"
        "Return:\n"
        "- key pain points\n"
        "- real disagreements\n"
        "- non-obvious insights\n"
        "- language people use\n\n"
        "Be concise."
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": prompt
            },
            timeout=10
        )

        if response.ok:
            body = response.json()
            text_output = extract_openai_text(body)

            sources.append({
                "id": "openai-1",
                "title": "OpenAI synthesis",
                "url": None,
                "text": text_output,
                "source_type": "openai"
            })
        else:
            sources.append({
                "id": "openai-error",
                "title": "OpenAI error",
                "url": None,
                "text": response.text,
                "source_type": "provider_error"
            })

    except Exception as e:
        sources.append({
            "id": "openai-exception",
            "title": "OpenAI exception",
            "url": None,
            "text": str(e),
            "source_type": "provider_error"
        })

    return sources


def extract_openai_text(body: Dict) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]

    try:
        output = body.get("output", [])
        parts: List[str] = []

        for item in output:
            for content in item.get("content", []):
                if isinstance(content, dict):
                    if isinstance(content.get("text"), str):
                        parts.append(content["text"])
                    elif isinstance(content.get("content"), str):
                        parts.append(content["content"])

        if parts:
            return "\n".join(parts)

    except Exception:
        pass

    return str(body)[:2000]
