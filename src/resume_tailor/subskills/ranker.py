"""
Resume Intelligence Ranker — Step 2A of the resume-tailor pipeline.

rank(jd_analysis, parsed_master) -> dict
  Pure Python — no Claude call.
  Scores every bullet against the JD analysis.
  Scores topics by average of their top-3 bullet scores.
  Allocates bullet budget proportionally across top-scoring topics.
  Returns ranked candidates organised by section → topic for 2B.
  Writes scratch/02a-ranked-bullets.json.
"""
import json
import re
from pathlib import Path

from resume_tailor.subskills.master_parser import TOPIC_SLUGS

SCRATCH_FILE = Path(__file__).parents[3] / "scratch" / "02a-ranked-bullets.json"

# ── Scoring weights (max total = 100) ───────────────────────────────────────
WEIGHTS = {
    "anchor_match":    30,  # JD anchor_list tool/tech found in bullet
    "keyword_overlap": 25,  # JD frequency_score terms found in bullet
    "gap_relevance":   20,  # bullet addresses a the_gap pain point
    "has_metric":      15,  # bullet contains a concrete number/percentage
    "mirror_verb":     10,  # bullet opens with a JD mirror_verb
}

# ── Section config ───────────────────────────────────────────────────────────
# parsed_path: (top_key, project_slug) into the master_parser result dict
SECTIONS = {
    "ai_engineer": {
        "parsed_path":    ("experience", "exp"),
        "budget":          2,
        "max_topics":      2,
        "min_score_pct":   0.65,
    },
    "mosaic": {
        "parsed_path":    ("projects", "mosaic"),
        "budget":          3,
        "max_topics":      2,
        "min_score_pct":   0.65,
    },
    "education": {
        "parsed_path":    ("projects", "weather"),
        "budget":          1,
        "max_topics":      1,
        "min_score_pct":   1.0,
    },
}

# Candidate pool sent to 2B = allocated_bullets + EXTRA_POOL (gives 2B real choices)
EXTRA_POOL = 2

# Regex: a bullet "has a metric" if it contains a percentage, 3+-digit number, or decimal
_METRIC_RE = re.compile(r"(\d+\.?\d*\s*%|\b\d{3,}\b|\d+\.\d+|\d+\s*[×x]\b)", re.IGNORECASE)

# Stopwords for gap_relevance significance filtering. Keeps short acronyms (RAG, LLM,
# AI, ETL, API, NLP, ML, GPU, IO) which a length-based filter would drop.
_STOPWORDS = {
    "the", "a", "an", "of", "and", "to", "in", "for", "with", "on", "by", "from",
    "is", "are", "be", "was", "were", "as", "at", "or", "but", "if", "this",
    "that", "it", "its", "their", "them", "we", "our", "you", "your", "have",
    "has", "had", "will", "would", "should", "could", "can", "may", "via",
    "into", "onto", "than", "then", "also", "such", "any", "all", "must",
    "need", "able", "using", "used", "use", "not", "no", "do", "does", "did",
}

# Word-extraction regex: alphanumerics only, lowercased. Splits "retrieval-augmented"
# into ["retrieval", "augmented"] and strips trailing punctuation.
_WORD_RE = re.compile(r"[a-z0-9]+")


# ── Bullet scoring ───────────────────────────────────────────────────────────

def _normalised_terms(items: list[str]) -> list[str]:
    return [t.lower().strip() for t in items if t.strip()]


def _verb_root(word: str) -> str:
    """Crude verb stemmer — strips common regular suffixes.
    Handles Designing/design, Achieved/achieve, Architects/architect.
    Does NOT handle irregulars (Built/build, Wrote/write) — accepted miss."""
    w = word.lower().rstrip(".,;:")
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _gap_sig_words(gap: str) -> list[str]:
    """Significant tokens from a gap statement: alphanumeric words minus stopwords.
    Preserves short acronyms (RAG, LLM, AI) that a length filter would drop."""
    return [w for w in _WORD_RE.findall(gap.lower()) if w not in _STOPWORDS]


def _score_bullet(text: str, jd: dict, topic_slug: str = "") -> dict[str, float]:
    lower = text.lower()

    # anchor_match: hard_requirements from anchor_metadata (non-negotiables only)
    anchors = _normalised_terms(
        jd.get("anchor_metadata", {}).get("hard_requirements", [])
    )
    anchor_hits = sum(1 for t in anchors if t in lower)
    anchor_score = (anchor_hits / max(len(anchors), 1)) * WEIGHTS["anchor_match"]

    # keyword_overlap: frequency_score terms (already normalised by Agent 1)
    freq_terms = _normalised_terms([e["term"] for e in jd.get("frequency_score", [])])
    freq_hits = sum(1 for t in freq_terms if t in lower)
    kw_score = (freq_hits / max(len(freq_terms), 1)) * WEIGHTS["keyword_overlap"]

    # gap_relevance: slug match (exact, high confidence) then text match (fallback).
    # Slug match: bullet's topic slug == gap's target_topic_slug → full credit for that gap.
    # Text match: significant words from gap text found in bullet → partial signal.
    gap_score = 0.0
    gap_mappings = jd.get("gap_mapping", [])
    if gap_mappings:
        gap_hits = 0
        for gm in gap_mappings:
            target_slug = gm.get("target_topic_slug", "")
            if topic_slug and target_slug and topic_slug == target_slug:
                gap_hits += 1  # exact slug match — high confidence
            else:
                sig_words = _gap_sig_words(gm.get("gap", ""))
                if any(w in lower for w in sig_words):
                    gap_hits += 1  # text match — fallback signal
        gap_score = (gap_hits / len(gap_mappings)) * WEIGHTS["gap_relevance"]

    # has_metric: concrete number present
    metric_score = WEIGHTS["has_metric"] if _METRIC_RE.search(text) else 0.0

    # mirror_verb: stemmed first word matches a stemmed JD mirror_verb
    tokens = text.split()
    first_word = tokens[0].rstrip(".,;:").lower() if tokens else ""
    first_root = _verb_root(first_word) if first_word else ""
    verb_roots = {_verb_root(v) for v in _normalised_terms(jd.get("mirror_verbs", []))}
    verb_score = WEIGHTS["mirror_verb"] if first_root and first_root in verb_roots else 0.0

    return {
        "anchor_match":    round(anchor_score, 1),
        "keyword_overlap": round(kw_score, 1),
        "gap_relevance":   round(gap_score, 1),
        "has_metric":      metric_score,
        "mirror_verb":     verb_score,
        "total":           round(anchor_score + kw_score + gap_score + metric_score + verb_score, 1),
    }


# ── Topic scoring ────────────────────────────────────────────────────────────

def _score_topic(scored_bullets: list[dict]) -> float:
    """Average of the top-3 bullet totals in this topic."""
    totals = sorted([b["score"]["total"] for b in scored_bullets], reverse=True)
    top = totals[:3]
    return round(sum(top) / len(top), 1) if top else 0.0


# ── Budget allocation ────────────────────────────────────────────────────────

def _allocate_topics(
    topic_scores: dict[str, float],
    budget: int,
    max_topics: int,
    min_score_pct: float,
) -> dict[str, int]:
    """
    Returns {topic_name: n_bullets_allocated}.
    Only topics scoring >= min_score_pct of the top score survive.
    Allocation is proportional; every surviving topic gets at least 1 bullet.
    """
    if not topic_scores:
        return {}

    top_score = max(topic_scores.values())
    threshold = top_score * min_score_pct

    eligible = sorted(
        [(t, s) for t, s in topic_scores.items() if s >= threshold],
        key=lambda x: x[1],
        reverse=True,
    )[:max_topics]

    if not eligible:
        # Fallback: threshold matched nothing — take the top-scoring topic unconditionally
        top = max(topic_scores.items(), key=lambda x: x[1])
        print(
            f"[ranker] WARNING: no topics met threshold "
            f"({min_score_pct:.0%} of {top_score}). Falling back to: {top[0]!r}"
        )
        return {top[0]: budget}

    if len(eligible) == 1:
        return {eligible[0][0]: budget}

    total = sum(s for _, s in eligible)
    allocation: dict[str, int] = {}
    remaining = budget

    for i, (topic, score) in enumerate(eligible[:-1]):
        share = round(budget * score / total)
        # Ensure at least 1 per topic and leave at least 1 for remaining topics
        share = max(1, min(share, remaining - (len(eligible) - i - 1)))
        allocation[topic] = share
        remaining -= share

    allocation[eligible[-1][0]] = remaining
    return allocation


# ── Public API ───────────────────────────────────────────────────────────────

def rank(jd_analysis: dict, parsed_master: dict) -> dict:
    """
    Score and rank bullets from parsed_master against jd_analysis.

    Returns a ranked_candidates dict ready for 2B:
    {
      "ai_engineer": {
        "Email RAG System": {
          "allocated_bullets": 2,
          "candidates": [
            {"id": "...", "text": "...", "voice": "...", "score": {...}}
          ]
        }
      },
      "mosaic": { ... },
      "education": { ... }
    }
    """
    output: dict = {}
    debug: dict = {}  # full score breakdown for scratch file

    for section_key, cfg in SECTIONS.items():
        top_key, proj_slug = cfg["parsed_path"]
        project_data: dict = parsed_master.get(top_key, {}).get(proj_slug, {})

        # Score every bullet in every topic
        topic_scored: dict[str, list[dict]] = {}
        for topic_name, bullets in project_data.items():
            topic_slug = TOPIC_SLUGS.get(topic_name, "")
            scored = []
            for b in bullets:
                score = _score_bullet(b["text"], jd_analysis, topic_slug)
                scored.append({
                    "id":    b["id"],
                    "text":  b["text"],
                    "voice": b["voice"],
                    "score": score,
                })
            scored.sort(key=lambda x: x["score"]["total"], reverse=True)
            topic_scored[topic_name] = scored

        # Score topics
        topic_scores = {t: _score_topic(bullets) for t, bullets in topic_scored.items()}

        # Allocate budget
        allocation = _allocate_topics(
            topic_scores,
            budget=cfg["budget"],
            max_topics=cfg["max_topics"],
            min_score_pct=cfg["min_score_pct"],
        )

        # Build candidates per allocated topic
        section_out: dict = {}
        for topic_name, n_bullets in allocation.items():
            pool_size = n_bullets + EXTRA_POOL
            candidates = topic_scored[topic_name][:pool_size]
            section_out[topic_name] = {
                "allocated_bullets": n_bullets,
                "candidates": candidates,
            }

        output[section_key] = section_out

        # Debug entry
        debug[section_key] = {
            "topic_scores": topic_scores,
            "allocation":   allocation,
            "all_scored":   {t: b for t, b in topic_scored.items()},
        }

    SCRATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCRATCH_FILE.write_text(json.dumps({"ranked": output, "debug": debug}, indent=2), encoding="utf-8")
    print(f"[ranker] scratch -> {SCRATCH_FILE}")

    return output
