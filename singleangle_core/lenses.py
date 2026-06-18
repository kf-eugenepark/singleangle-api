from typing import List, Dict

LENSES = [
    {
        "name": "reframe",
        "question": "What is the popular interpretation missing? What hidden mechanism explains the topic better?"
    },
    {
        "name": "tension",
        "question": "Where is the real disagreement among credible operators?"
    },
    {
        "name": "hidden_cost",
        "question": "What downstream price is nobody pricing in?"
    },
    {
        "name": "leading_indicator",
        "question": "What bigger shift is this topic an early signal for?"
    },
    {
        "name": "category_error",
        "question": "Is the debate asking the wrong question or using the wrong category?"
    },
    {
        "name": "counter_case",
        "question": "What named counterexample breaks the consensus?"
    }
]


def generate_candidate_angles(topic: str, audience: str, sources: List[Dict]) -> List[Dict]:
    """
    Generates one candidate angle per lens.

    This starter uses deterministic templates to preserve the pipeline shape.
    Replace template generation with LLM calls or richer NLP if desired.
    """
    source_count = len(sources)
    audience_clause = f" for {audience}" if audience else ""

    templates = {
        "reframe": f"The obvious story about {topic} is too surface-level; the better read is the behavioral shift underneath it{audience_clause}.",
        "tension": f"The real argument about {topic} is not adoption versus skepticism, but who can prove operational value{audience_clause}.",
        "hidden_cost": f"The hidden cost of {topic} is the coordination drag it creates after the initial excitement fades{audience_clause}.",
        "leading_indicator": f"{topic} is a leading indicator that teams are moving from narrative-led strategy to proof-led execution{audience_clause}.",
        "category_error": f"Most debate around {topic} treats it as a tool question when it is really an operating-model question{audience_clause}.",
        "counter_case": f"The strongest counter-case on {topic} is any operator getting durable results without adopting the consensus playbook{audience_clause}."
    }

    candidates = []
    for lens in LENSES:
        candidates.append({
            "lens": lens["name"],
            "lens_question": lens["question"],
            "angle": templates[lens["name"]],
            "evidence_count": source_count
        })
    return candidates
