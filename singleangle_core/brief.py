from typing import List, Dict, Any


def assemble_brief(topic: str, audience: str, sources: List[Dict], scored_angles: List[Dict]) -> Dict[str, Any]:
    winner = scored_angles[0] if scored_angles else None
    runner_ups = scored_angles[1:3] if len(scored_angles) > 1 else []

    evidence_note = (
        "No external sources were provided or collected. Treat this as an angle-generation draft, not a sourced research brief."
        if not sources else
        f"Based on {len(sources)} provided or collected source item(s)."
    )

    angle_text = winner["angle"] if winner else f"No candidate angle generated for {topic}."

    return {
        "topic": topic,
        "audience": audience,
        "evidence_note": evidence_note,
        "winning_angle": winner,
        "runner_up_angles": runner_ups,
        "brief": {
            "angle_statement": angle_text,
            "hooks": build_hooks(topic, angle_text),
            "pro_arguments": build_pro_arguments(topic, angle_text),
            "counterarguments": build_counterarguments(topic),
            "stats": extract_stats(sources),
            "quotes": extract_quotes(sources),
            "story_moment": build_story_moment(topic, angle_text),
            "closing_lines": build_closing_lines(topic, angle_text)
        },
        "sources": summarize_sources(sources)
    }


def build_hooks(topic: str, angle: str) -> List[str]:
    return [
        f"Most people are reading {topic} at the surface. The sharper read is underneath it.",
        f"The useful question about {topic} is not whether it works. It is what it reveals.",
        f"The obvious take on {topic} is already crowded. This is the angle worth exploring."
    ]


def build_pro_arguments(topic: str, angle: str) -> List[str]:
    return [
        "The angle shifts the conversation from broad opinion to a more testable mechanism.",
        "It gives the writer a differentiated point of view without relying on contrarianism alone.",
        "It creates room for evidence, examples, and counterpoints instead of a one-note claim."
    ]


def build_counterarguments(topic: str) -> List[str]:
    return [
        f"The angle may overstate the significance of {topic} if the evidence base is thin.",
        "The audience may need concrete examples before accepting the framing.",
        "If the market already believes this, the angle needs a sharper proof point."
    ]


def extract_stats(sources: List[Dict]) -> List[Dict]:
    # Placeholder: add regex/stat extraction or provider metadata here.
    return []


def extract_quotes(sources: List[Dict]) -> List[Dict]:
    # Placeholder: add quote extraction from source text here.
    return []


def build_story_moment(topic: str, angle: str) -> str:
    return f"Open with a team or operator who adopted the obvious {topic} playbook, then discovered the real issue was the operating constraint underneath."


def build_closing_lines(topic: str, angle: str) -> List[str]:
    return [
        f"The point is not to be louder about {topic}. It is to be more precise about what it changes.",
        "The strongest strategy is not the one with the cleanest narrative. It is the one that survives contact with execution.",
        "The angle worth writing is the one that makes the reader see a familiar trend as a different problem."
    ]


def summarize_sources(sources: List[Dict]) -> List[Dict]:
    return [
        {
            "id": s.get("id"),
            "title": s.get("title"),
            "url": s.get("url"),
            "source_type": s.get("source_type"),
            "excerpt": (s.get("text", "")[:280] + "...") if len(s.get("text", "")) > 280 else s.get("text", "")
        }
        for s in sources
    ]
