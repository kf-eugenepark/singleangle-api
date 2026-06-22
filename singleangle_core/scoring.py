from typing import List, Dict
import re


def score_angles(candidates: List[Dict], sources: List[Dict], audience: str = "") -> List[Dict]:
    scored = []
    all_source_text = "\n".join([s.get("text", "") for s in sources]).lower()

    for candidate in candidates:
        angle = candidate["angle"]
        scores = {
            "stop_scroll": score_stop_scroll(angle),
            "compression": score_compression(angle),
            "non_consensus": score_non_consensus(angle, all_source_text),
            "relevance": score_relevance(angle, audience)
        }
        weighted_total = (
            scores["stop_scroll"] * 0.30 +
            scores["compression"] * 0.20 +
            scores["non_consensus"] * 0.30 +
            scores["relevance"] * 0.20
        )
        scored.append({
            **candidate,
            "scores": scores,
            "weighted_total": round(weighted_total, 3)
        })

    return sorted(scored, key=lambda item: item["weighted_total"], reverse=True)


def score_stop_scroll(angle: str) -> float:
    # Rewards specificity and a clear contradiction/tension.
    tension_terms = ["hidden", "real", "wrong", "better", "not", "underneath", "cost", "proof"]
    term_hits = sum(1 for term in tension_terms if term in angle.lower())
    return clamp(0.45 + min(term_hits, 4) * 0.12)


def score_compression(angle: str) -> float:
    # Rewards concise angles that can fit in a hook.
    words = len(angle.split())
    if words <= 18:
        return 1.0
    if words <= 28:
        return 0.8
    if words <= 40:
        return 0.6
    return 0.4


def score_non_consensus(angle: str, all_source_text: str) -> float:
    # Simple proxy: if the angle contains uncommon framing words, reward it.
    # Replace this with source-aware semantic similarity if needed.
    uncommon_terms = ["category", "operating-model", "coordination", "behavioral", "proof-led", "counter-case"]
    hits = sum(1 for term in uncommon_terms if term in angle.lower())
    return clamp(0.55 + min(hits, 3) * 0.12)


def score_relevance(angle: str, audience: str) -> float:
    if not audience:
        return 0.65
    audience_tokens = set(re.findall(r"[a-zA-Z0-9]+", audience.lower()))
    angle_tokens = set(re.findall(r"[a-zA-Z0-9]+", angle.lower()))
    overlap = len(audience_tokens.intersection(angle_tokens))
    return clamp(0.70 + min(overlap, 3) * 0.08)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(max(low, min(high, value)), 3)
