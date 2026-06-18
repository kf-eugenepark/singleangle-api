from typing import List, Dict, Optional


def openai_reddit_research(topic: str, audience: str, api_key: Optional[str], model: str = "gpt-5", web_search_tool: str = "web_search_preview") -> List[Dict]:
    """
    Uses OpenAI Responses API as a research/synthesis provider for Reddit-style discourse.

    Important:
    - This is not the Reddit API.
    - When OpenAI web search is available for your key/model, the request attempts to bias toward Reddit and forum results.
    - If the web search tool is unavailable, it returns an error source instead of silently inventing sources.
    """
    if not api_key:
        return [{
            "id": "openai-missing-key",
            "title": "OpenAI key missing",
            "url": None,
            "source_type": "provider_status",
            "text": "OpenAI research skipped because OPENAI_API_KEY is not configured."
        }]

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    prompt = f"""
You are researching Reddit/forum discourse for a content strategy brief.

Topic: {topic}
Audience: {audience or 'general business audience'}

Find and synthesize Reddit-like discussion patterns. Prefer Reddit, forums, and practitioner discussions when available.
Return concise notes with:
1. recurring pain points
2. common disagreements
3. surprising operator insights
4. language people actually use
5. risks or weak evidence

Do not invent exact quotes or URLs. If you cannot verify sources, say so clearly.
"""

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            tools=[{"type": web_search_tool}],
        )
        text = getattr(response, "output_text", None) or str(response)
        source_type = "openai_reddit_web_research"
    except Exception as e:
        return [{
            "id": "openai-error",
            "title": "OpenAI Reddit research failed",
            "url": None,
            "source_type": "provider_error",
            "text": f"OpenAI research failed. Check OPENAI_API_KEY, OPENAI_MODEL, and OPENAI_WEB_SEARCH_TOOL. Error: {str(e)}"
        }]

    return [{
        "id": "openai-reddit-1",
        "title": "OpenAI Reddit/forum discourse research",
        "url": None,
        "source_type": source_type,
        "text": text
    }]


def xai_x_research(topic: str, audience: str, api_key: Optional[str], model: str = "grok-4.3") -> List[Dict]:
    """
    Uses xAI/Grok via the OpenAI-compatible chat completions API as an X discourse analysis provider.

    Important:
    - This starter uses chat completions against xAI's OpenAI-compatible endpoint.
    - It does not yet implement a dedicated X Search tool call.
    - Treat output as discourse synthesis unless your xAI account/model/tooling provides live X search context.
    """
    if not api_key:
        return [{
            "id": "xai-missing-key",
            "title": "xAI key missing",
            "url": None,
            "source_type": "provider_status",
            "text": "xAI research skipped because XAI_API_KEY is not configured."
        }]

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You analyze X/Twitter discourse for content strategy. Be concise, skeptical, and source-conscious. Do not invent exact tweets."
                },
                {
                    "role": "user",
                    "content": f"""
Analyze X/Twitter-style discourse for this topic:

Topic: {topic}
Audience: {audience or 'general business audience'}

Return:
1. dominant opinion
2. credible disagreement
3. overlooked angle
4. phrases or language patterns people use
5. risks of writing about this topic

If you cannot verify live X data, state that clearly and frame output as synthesis.
"""
                }
            ],
            temperature=0.2,
        )
        text = completion.choices[0].message.content
    except Exception as e:
        return [{
            "id": "xai-error",
            "title": "xAI X research failed",
            "url": None,
            "source_type": "provider_error",
            "text": f"xAI research failed. Check XAI_API_KEY and XAI_MODEL. Error: {str(e)}"
        }]

    return [{
        "id": "xai-x-1",
        "title": "xAI/Grok X discourse synthesis",
        "url": None,
        "source_type": "xai_x_synthesis",
        "text": text
    }]
