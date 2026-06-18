from typing import List, Dict

LENSES = [
    {"name": "reframe", "question": "What is the popular interpretation missing? What hidden mechanism explains the topic better?"},
    {"name": "tension", "question": "Where is the real disagreement among credible operators?"},
    {"name": "hidden_cost", "question": "What downstream price is nobody pricing in?"},
    {"name": "leading_indicator", "question": "What bigger shift is this topic an early signal for?"},
    {"name": "category_error", "question": "Is the debate asking the wrong question or using the wrong category?"},
    {"name": "counter_case", "question": "What named counterexample breaks the consensus?"}
]


def _source_signal(sources: List[Dict]) -> str:
    snippets = []
    for s in sources[:4]:
        txt = (s.get("text") or "").replace("\n", " ").strip()
        if txt:
            snippets.append(txt[:240])
    return " | ".join(snippets)


def generate_candidate_angles(topic: str, audience: str, sources: List[Dict]) -> List[Dict]:
    source_count = len(sources)
    signal = _source_signal(sources)
    audience_clause = f" for {audience}" if audience else ""

    # Still deterministic, but now uses source signal to make the templates less generic.
    evidence_hint = f" Evidence signal: {signal}" if signal else ""

    templates = {
        "reframe": f"{topic} should be judged less by surface output quality and more by the system constraints shaping results{audience_clause}.{evidence_hint}",
        "tension": f"The useful debate around {topic} is between visible adoption and provable operating value{audience_clause}.{evidence_hint}",
        "hidden_cost": f"The hidden cost of {topic} is the extra coordination, data hygiene, and judgment work it pushes downstream{audience_clause}.{evidence_hint}",
        "leading_indicator": f"{topic} is an early signal that teams are shifting from content volume to proof of execution quality{audience_clause}.{evidence_hint}",
        "category_error": f"Most discussion of {topic} treats it as a tooling problem when the failure mode is usually a workflow and targeting problem{audience_clause}.{evidence_hint}",
        "counter_case": f"The counter-case on {topic} is that teams can outperform the consensus playbook by improving targeting, offer quality, and process discipline first{audience_clause}.{evidence_hint}"
    }

    return [{
        "lens": lens["name"],
        "lens_question": lens["question"],
        "angle": templates[lens["name"]],
        "evidence_count": source_count
    } for lens in LENSES]
