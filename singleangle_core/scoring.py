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
            "relevance": score_relevance(angle, audience),
            "evidence": score_evidence(candidate, sources)
        }
        weighted_total = (
            scores["stop_scroll"] * 0.25 +
            scores["compression"] * 0.15 +
            scores["non_consensus"] * 0.25 +
            scores["relevance"] * 0.15 +
            scores["evidence"] * 0.20
        )
        scored.append({**candidate, "scores": scores, "weighted_total": round(weighted_total, 3)})

    return sorted(scored, key=lambda item: item["weighted_total"], reverse=True)


def score_stop_scroll(angle: str) -> float:
    tension_terms = ["hidden", "less", "more", "failure", "proof", "outperform", "constraints", "downstream"]
    term_hits = sum(1 for term in tension_terms if term in angle.lower())
    return clamp(0.45 + min(term_hits, 4) * 0.12)


def score_compression(angle: str) -> float:
    words = len(angle.split())
    if words <= 22: return 1.0
    if words <= 35: return 0.8
    if words <= 55: return 0.6
    return 0.4


def score_non_consensus(angle: str, all_source_text: str) -> float:
    uncommon_terms = ["constraints", "coordination", "data hygiene", "workflow", "targeting", "proof", "operating value"]
    hits = sum(1 for term in uncommon_terms if term in angle.lower())
    return clamp(0.50 + min(hits, 4) * 0.11)


def score_relevance(angle: str, audience: str) -> float:
    if not audience: return 0.65
    audience_tokens = set(re.findall(r"[a-zA-Z0-9]+", audience.lower()))
    angle_tokens = set(re.findall(r"[a-zA-Z0-9]+", angle.lower()))
    overlap = len(audience_tokens.intersection(angle_tokens))
    return clamp(0.70 + min(overlap, 3) * 0.08)


def score_evidence(candidate: Dict, sources: List[Dict]) -> float:
    if not sources: return 0.35
    provider_errors = [s for s in sources if s.get("source_type") == "provider_error"]
    useful = [s for s in sources if s.get("source_type") not in ("provider_error", "provider_status")]
    base = 0.45 + min(len(useful), 4) * 0.10
    if provider_errors:
        base -= 0.10
    return clamp(base)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(max(low, min(high, value)), 3)
