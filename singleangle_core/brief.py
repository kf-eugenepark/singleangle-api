from typing import List, Dict, Any


def assemble_brief(topic: str, audience: str, sources: List[Dict], scored_angles: List[Dict]) -> Dict[str, Any]:
    winner = scored_angles[0] if scored_angles else None
    runner_ups = scored_angles[1:3] if len(scored_angles) > 1 else []

    useful_sources = [s for s in sources if s.get("source_type") not in ("provider_error", "provider_status")]
    errors = [s for s in sources if s.get("source_type") == "provider_error"]
    statuses = [s for s in sources if s.get("source_type") == "provider_status"]

    if not useful_sources:
        evidence_note = "No usable external or provided sources were collected. Treat this as an unsourced angle draft."
    else:
        evidence_note = f"Based on {len(useful_sources)} usable source item(s)."
        if errors or statuses:
            evidence_note += " Some providers returned warnings or were skipped."

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
        f"The lazy take on {topic} is about the tool. The useful take is about the system around it.",
        f"If {topic} feels disappointing, the bottleneck may not be the model. It may be the operating inputs around it.",
        f"The teams winning with {topic} are probably not using better prompts. They are using better process discipline."
    ]


def build_pro_arguments(topic: str, angle: str) -> List[str]:
    return [
        "The angle moves the discussion from vague adoption claims to a testable operating mechanism.",
        "It gives the writer a practical POV that can be supported with examples from process, data quality, and execution.",
        "It avoids empty contrarianism by tying the claim to specific failure modes."
    ]


def build_counterarguments(topic: str) -> List[str]:
    return [
        f"The angle may overstate the role of operating discipline if {topic} is still limited by technical capability.",
        "The audience may need concrete examples before accepting the reframing.",
        "If the market already believes this, the post needs a sharper proof point or named counter-case."
    ]


def extract_stats(sources: List[Dict]) -> List[Dict]:
    return []


def extract_quotes(sources: List[Dict]) -> List[Dict]:
    return []


def build_story_moment(topic: str, angle: str) -> str:
    return f"Open with a team that adopted the standard {topic} playbook, saw mediocre results, and later discovered the issue was not the tool but the quality of targeting, inputs, and follow-through."


def build_closing_lines(topic: str, angle: str) -> List[str]:
    return [
        f"The point is not to be more enthusiastic about {topic}. It is to be more precise about what actually makes it work.",
        "Better tools do not rescue weak systems. They expose them faster.",
        "The useful edge is not having the newest workflow. It is knowing which part of the workflow actually creates leverage."
    ]


def summarize_sources(sources: List[Dict]) -> List[Dict]:
    return [{
        "id": s.get("id"),
        "title": s.get("title"),
        "url": s.get("url"),
        "source_type": s.get("source_type"),
        "excerpt": (s.get("text", "")[:500] + "...") if len(s.get("text", "")) > 500 else s.get("text", "")
    } for s in sources]
